# Plan: Save Orders to Google Sheets

> Note: an interactive plan-approval flow was attempted; the user instead asked for the full
> plan as a project markdown file. This file is that plan. Nothing has been implemented yet.

## Context

Vendors currently have no structured order record — only per-customer lifecycle statuses
(`INQUIRY → WAITING_VENDOR_CHECKOUT_APPROVAL → ACCOUNT_DETAILS_SENT`). This feature:

- persists every finalized order to **our database** (new `orders` table),
- optionally appends each order as a row to the **vendor's Google Sheet** (per-vendor toggle),
- survives Sheets failures via persist + retry (background sweep) and surfaces sync issues in the settings UI.

Decisions made with the user:

1. **Auth — per-vendor Google OAuth** (not a service account), separate from the existing
   Google Contacts token (the `spreadsheets` scope requires its own consent anyway).
   Vendors connect whichever Google account they choose (Google's account picker; if they
   signed up with Google they'll typically pick the same one) and can disconnect/reconnect
   to switch accounts.
2. **Order moment** — one row when payment details are sent to the customer
   (lifecycle transition to `ACCOUNT_DETAILS_SENT`). Both the auto-send path and the
   vendor-approve path funnel through `webhook_service.py`.
3. **Failure model** — orders are always written to the DB first with sync state; failed
   appends are retried by a periodic sweep; vendor sees reconnect / sync-issue status in settings.

### Google Sheets API facts (researched from official docs)

- Quotas: **300 write requests/min per project**, **60/min per user per project**; quota errors
  return HTTP 429 and should be retried with truncated exponential backoff.
- Each `values().append` call counts as **one** write request regardless of cells/rows.
- 2 MB recommended payload cap (we write one row — a non-issue).
- Auth: `googleapiclient.discovery.build("sheets", "v4", credentials=...)` with
  OAuth user credentials (`google.oauth2.credentials.Credentials`), scopes
  `https://www.googleapis.com/auth/spreadsheets`.
- Client libs are sync → must run through `asyncio.to_thread` in this async app.
- Rate-limit pricing: currently free; exceeding quota may be charged "later in 2026" —
  retry-with-backoff keeps us inside quota.

## Implementation steps

### 1. DB — `app/repositories/models.py` + migration

New tables after `VendorGoogleToken` (models.py:179):

- **`orders`**: `id` PK, `vendor_id` FK index, `customer_id` FK (SET NULL), `status`
  (default `'ACCOUNT_DETAILS_SENT'`), `order_ref` unique (`ORD-{id:06d}`, generated in-repo
  after insert, before flush — this is the duplicate-guard key), denormalized customer
  snapshot (`customer_name`, `customer_phone`, `customer_platform`, `customer_handle`, `note`),
  sync state (`sheets_synced` bool index, `sheets_sync_attempts`, `sheets_synced_at`,
  `sheets_last_error`, `next_attempt_at` index, `sync_claimed_until`), timestamps.
- **`vendor_google_sheets_tokens`**: same shape as `VendorGoogleToken`, separate table.

Extend `VendorBotSetting` (models.py:51) with: `sheets_sync_enabled` (default 0),
`sheets_spreadsheet_id`, `sheets_spreadsheet_title`, `sheets_tab_name`.

Migration: `alembic/versions/20260908_01_orders_sheets.py`, copying the guard-helper idiom
(`_table_exists` / `_column_exists`) from `20260605_01_telegram_support.py`;
`down_revision = "20260605_01"`. Dev/test get the tables automatically via
`init_db` (`Base.metadata.create_all`); the migration covers production DBs.

### 2. Interfaces + SQL repos — `app/domain/interfaces.py`, `app/repositories/sql.py`

- `GoogleSheetsTokenRepository` protocol — clone of `GoogleTokenRepository` (interfaces.py:118);
  SQL impl is a small clone of `SQLGoogleTokenRepository` (sql.py:844).
- `OrderRepository` protocol:
  - `create_order(vendor_id, payload) -> dict | None`
  - `mark_synced(order_id) -> None`
  - `record_sync_failure(order_id, error, retry_delay_seconds) -> None`
  - `claim_pending(limit=50) -> list[dict]` — multi-worker guard:
    `UPDATE orders SET sync_claimed_until = now + 5min WHERE sheets_synced = 0
    AND (next_attempt_at IS NULL OR <= now) AND (sync_claimed_until IS NULL OR <= now)`,
    then re-select rows with that exact claim expiry. Two workers can't claim the same row.
  - `list_pending_for_vendor(vendor_id) -> list[dict]`
  - `count_for_vendor(vendor_id, synced: bool) -> int`
- `SQLVendorSettingsRepository.get`/`upsert` (sql.py:820): add the 4 new keys to the
  defaults dict and row mapping (upsert's generic `setattr` needs no change).

### 3. Config — `app/config.py`

- `google_sheets_redirect_uri` (`GOOGLE_SHEETS_REDIRECT_URI`, default
  `http://localhost:8001/auth/google/sheets/callback`)
- `sheets_sweep_enabled` (default True)
- `sheets_sweep_interval_seconds` (default 300)

### 4. OAuth service — new `app/services/google_sheets_oauth_service.py`

Mirror `GoogleOAuthService` (google_oauth_service.py) with
`SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]`:
reuse `_build_state` / `_parse_state` (already staticmethods — import, don't copy);
same `prompt="consent"`, `access_type="offline"` (refresh token always granted),
`asyncio.to_thread(flow.fetch_token, ...)`, refresh-on-expiry, and status dict shape
(`connected` / `not_connected` / `invalid_credentials` / `refresh_failed`).

### 5. Sync service — new `app/services/google_sheets_service.py`

```python
class GoogleSheetsService:
    MAX_RETRIES = 3

    def __init__(self, settings, tokens: GoogleSheetsTokenRepository,
                 orders: OrderRepository, settings_repo: VendorSettingsRepository) ...

    async def validate_spreadsheet(vendor_id: int, url: str) -> dict   # {id, title, tab_name}
    async def sync_order(order: dict) -> bool
    async def sweep_pending(limit: int = 50) -> None
    @staticmethod
    def extract_spreadsheet_id(url_or_id: str) -> str
```

- `validate_spreadsheet`: build client (`cache_discovery=False`),
  `spreadsheets().get()` via `asyncio.to_thread`; 403/404 →
  `ValidationError("Spreadsheet not found or not shared with your Google account")`;
  `tab_name` = first sheet's `properties.title`.
- `extract_spreadsheet_id`: regex handles `https://docs.google.com/spreadsheets/d/{id}/edit`,
  `/d/{id}/`, bare id; rejects `/new`, `/create` (ValidationError).
- `sync_order(order)`:
  1. Load vendor settings; `sheets_sync_enabled` off or no `sheets_spreadsheet_id` →
     return False (row stays pending for later).
  2. `_get_credentials(vendor_id)` (pattern from google_contacts_service.py:32-46 with
     SHEETS_SCOPES); `None` (missing/refresh-fail) →
     `record_sync_failure(order_id, "reauth_needed", ...)`.
  3. **Duplicate guard — retries only** (`sheets_sync_attempts > 0`):
     `values().get("'{tab}'!A:A")`; if `order_ref` already in column A → `mark_synced`
     and return, no append (covers append-succeeded-but-response-lost).
  4. Append: `values().append(spreadsheetId, range="'{tab}'!A1", valueInputOption="RAW",
     insertDataOption="INSERT_ROWS", body={"values": [row]})` via retry helper
     (pattern from google_contacts_service.py:58-77): `asyncio.to_thread`, transient
     statuses `{408, 429, 500, 502, 503, 504}`, backoff `min(0.25 · 2^(n-1) + jitter, 8s)`.
  5. Success → `mark_synced(order_id)`. Failure → classify (403/404 →
     `spreadsheet_unavailable`; else raw error), `record_sync_failure` with retry delay
     `min(900 · 2^(attempts-1), 86400)` (15 min → 24 h cap).
- Row layout (7 cols, empty string for missing values — handles nameless customers and
  phone-less Instagram/Telegram customers):
  `[timestamp, order_ref, customer_name, customer_phone, customer_platform, customer_handle, status]`
- First append for a spreadsheet writes a header row if A1 is empty
  (`Timestamp, Order ID, Customer Name, Phone, Platform, Handle, Status`).
- `sweep_pending`: `claim_pending` → `sync_order` each in try/except (one bad row can't kill
  the loop); increment success/failure metrics via `get_metrics_registry()`.

### 6. Hook point — `app/services/webhook_service.py` (~line 108)

`if decision.order_status:` is the single funnel where both `ACCOUNT_DETAILS_SENT` paths
converge (agent_service auto-send + vendor approve). Extend it:

```python
if decision.order_status:
    previous = await self.customers.get_order_lifecycle_state(
        vendor_id=vendor["id"], customer_id=customer["id"])
    previous_status = (previous or {}).get("status")
    await self.customers.upsert_order_lifecycle_state(...)   # unchanged
    if decision.order_status == "ACCOUNT_DETAILS_SENT" and previous_status != "ACCOUNT_DETAILS_SENT":
        order = await self.orders.create_order(...)   # snapshot: name, whatsapp_number, platform, ig/tg id
        asyncio.create_task(self.sheets.sync_order(order))   # off the request path, log via done_callback
```

The `previous_status != "ACCOUNT_DETAILS_SENT"` check prevents duplicate orders on repeated
transitions or duplicate webhook deliveries; a genuine new order cycle passes through
WAITING_VENDOR_CHECKOUT_APPROVAL first, so it creates a fresh order.

Add `orders: OrderRepository` and `sheets: GoogleSheetsService | None` to
`WebhookService.__init__`; wire in `app/api/deps.py` (`get_order_repo`,
`get_google_sheets_token_repo`, `get_google_sheets_service`, extend `get_webhook_service`).

### 7. Sweep loop — `app/main.py`

In `_lifespan`: `asyncio.create_task(_sheets_sweep_loop())` when `sheets_sweep_enabled`;
loop = `sweep_pending()` in try/except, then `asyncio.sleep(interval)`; cancel on shutdown.
Multi-worker safe via `claim_pending`'s row claiming.

### 8. Schemas + routes

`app/schemas/api.py`:
- Extend `VendorSettingsResponse` / `VendorSettingsUpdateRequest` with `sheets_sync_enabled`.
- New `SheetsConfigUpdateRequest { spreadsheet_url: str }`.
- New `SheetsConfigResponse { google_connected, spreadsheet_id, spreadsheet_title,
  sync_enabled, sync_status, pending_orders, synced_orders, last_error }`.

`app/api/routes/auth.py` (mirror existing Google routes):
- `GET /auth/google/sheets?vendor_id=` → redirect to authorization URL.
- `GET /auth/google/sheets/callback` → complete token exchange, redirect
  `{frontend_base_url}/settings?sheets=connected`.
- `GET /auth/google/sheets/status?vendor_id=` → connection status.

`app/api/routes/vendor_admin.py` (with `_authorize_vendor_scope` + `_ensure_vendor`):
- `PUT /vendors/{id}/sheets-config` → extract id → `validate_spreadsheet` (token must
  exist; 403/404 → 400 with clear message) → persist id/title/tab +
  `sheets_sync_enabled=True` → return `SheetsConfigResponse`.
- `GET /vendors/{id}/sheets-config` → token status + settings + pending/synced counts +
  derived `sync_status` (`healthy` | `reauth_needed` | `spreadsheet_unavailable` | `error`).
- `DELETE /vendors/{id}/sheets-config` → delete sheets token, clear spreadsheet fields,
  `sheets_sync_enabled=False`.

**Toggle semantics**: turning off stops *new* syncs only; orders created while off remain
pending and sync when re-enabled; already-synced rows are never re-appended (synced flag +
order_ref guard). No duplicate backfill.

### 9. Frontend

`frontend/src/lib/api.ts`:
- `SheetsConfig` type + `fetchGoogleSheetsOAuthStatus` / `fetchSheetsConfig` /
  `updateSheetsConfig` / `disconnectSheets`.
- Extend `VendorBotSettings` with `sheets_sync_enabled: boolean`.

`frontend/src/app/(main)/settings/page.tsx`:
- Add `sheets_sync_enabled` row to `settingRows` — existing `toggleSetting` works unchanged.
- New "Orders Spreadsheet" section between Contact Integration and Bot Settings:
  - "Connect Google for Sheets" button → `{API_ROOT}/auth/google/sheets?vendor_id=...`
    (mirrors existing `handleGoogleConnect`), shown when not connected; "Disconnect" otherwise.
  - Spreadsheet URL input + Save (loading/error/success states; placeholder shows saved title).
  - Status line: `Status: {sync_status}` + pending/synced counts; "Reconnect Google" action
    when `reauth_needed`; "Check sharing settings" when `spreadsheet_unavailable`.
- Load config in the existing `Promise.allSettled` block alongside the other fetches.

## Edge cases handled

| Case | Handling |
|---|---|
| Token expired / refresh fails | `reauth_needed` recorded; UI shows reconnect prompt |
| Token revoked | Refresh fails → same path; status flips on next sweep |
| Sheet deleted or unshared | 403/404 → `spreadsheet_unavailable`; UI prompts check sharing |
| 429 quota | Transient set + truncated exponential backoff |
| Network failure mid-append (response lost) | Retry searches column A for `order_ref` before appending |
| Toggle off → on | Unsynced orders sync on re-enable; synced ones never re-append |
| Duplicate webhook / repeat transition | `previous_status` guard prevents duplicate order rows |
| Multi-worker double-append | `claim_pending` optimistic lock with 5-min claim expiry |
| Nameless customer / IG/TG (no phone) | Empty cells, handle/id in the snapshot |
| One bad order during sweep | Per-row try/except; loop continues |

## Verification

**Unit (no Google creds) — new `tests/test_sheets_orders.py`** (DummyAgent-style fakes;
monkeypatch `googleapiclient.discovery.build` or the service's sync methods):
1. Order row created + sync attempted on ACCOUNT_DETAILS_SENT transition.
2. Duplicate transition → no second order.
3. Append success → `mark_synced` called.
4. 429 → backoff retried, then success.
5. Failure → `record_sync_failure` with delay.
6. Retry sees `order_ref` already in column A → no duplicate append, marked synced.
7. No token → `reauth_needed` recorded.
8. 404 on validate → `ValidationError`.
9. `claim_pending` double-call → disjoint sets.
10. `extract_spreadsheet_id` URL forms (full URL, /d/ path, bare id, /new rejected).
11. IG/TG snapshot: empty name/phone, handle populated.

Run: `python -m pytest tests/`.

**Manual E2E (with real creds)**:
1. Register `http://localhost:8001/auth/google/sheets/callback` in Google Cloud Console
   (same OAuth client as Contacts).
2. Connect in settings; paste a test spreadsheet URL; verify validation + saved title.
3. Drive a checkout with confirm-toggle **on** (tap ✅ YES) and **off** (auto-send);
   verify sheet row + `orders` row with `sheets_synced=1`.
4. Revoke token at myaccount.google.com/permissions → status flips to `reauth_needed`.
5. Delete spreadsheet → `spreadsheet_unavailable` on next sweep.
6. Toggle off, place an order, toggle on → exactly one backfill row appears.

## Order of work

models + migration → interfaces + repos → sheets OAuth service → sync service →
webhook hook + deps → sweep loop → schemas + routes → frontend → tests.
Backend is independently testable at each step (init_db auto-creates tables in dev).

**Done signal**: play notification sound (`canberra-gtk-play -i complete`) when finished
or when user input is needed.
