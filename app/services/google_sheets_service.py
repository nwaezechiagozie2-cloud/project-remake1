"""Google Sheets order sync.

Appends each persisted order as a row to the vendor's spreadsheet. The
append runs off the request path; failures are recorded on the order row
and retried by the periodic sweep. Orders are the source of truth — a
sheet is a projection.
"""
import asyncio
import json
import logging
import random
import re
from datetime import datetime

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import Settings
from app.domain.interfaces import GoogleSheetsTokenRepository, OrderRepository, VendorSettingsRepository
from app.exceptions import ValidationError
from app.observability import get_metrics_registry
from app.services.google_sheets_oauth_service import SHEETS_SCOPES

logger = logging.getLogger(__name__)

_SPREADSHEET_URL_RE = re.compile(r"/spreadsheets/d/([-\w]{20,})")
_BARE_ID_RE = re.compile(r"^[-\w]{20,}$")

_HEADER_ROW = [
    "Timestamp",
    "Order ID",
    "Customer Name",
    "Phone",
    "Platform",
    "Handle",
    "Order Details",
    "Status",
]

# Retry delay for sweep-level failures: 15 min doubling up to a 24 h cap.
_SYNC_RETRY_BASE_SECONDS = 900
_SYNC_RETRY_MAX_SECONDS = 86400


class GoogleSheetsService:
    MAX_RETRIES = 3

    def __init__(
        self,
        settings: Settings,
        tokens: GoogleSheetsTokenRepository,
        orders: OrderRepository,
        settings_repo: VendorSettingsRepository,
    ) -> None:
        self.settings = settings
        self.tokens = tokens
        self.orders = orders
        self.settings_repo = settings_repo

    # ------------------------------------------------------------------ helpers

    async def _get_credentials(self, vendor_id: int) -> Credentials | None:
        token_json = await self.tokens.get_token_json(vendor_id)
        if not token_json:
            return None

        try:
            credentials = Credentials.from_authorized_user_info(json.loads(token_json), SHEETS_SCOPES)
        except Exception:
            logger.exception("google_sheets_token_invalid | vendor_id=%s", vendor_id)
            return None

        if credentials.expired and credentials.refresh_token:
            try:
                await asyncio.to_thread(credentials.refresh, GoogleRequest())
                await self.tokens.upsert_token_json(vendor_id, credentials.to_json())
            except Exception:
                get_metrics_registry().increment("failures_total")
                logger.exception("google_sheets_token_refresh_failed | vendor_id=%s", vendor_id)
                return None
        return credentials

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        if isinstance(exc, (TimeoutError, ConnectionError)):
            return True
        if isinstance(exc, HttpError):
            status = getattr(getattr(exc, "resp", None), "status", None)
            return status in {408, 409, 425, 429, 500, 502, 503, 504}
        text = str(exc).lower()
        return any(token in text for token in ("timed out", "timeout", "temporarily", "connection reset", "rate limit"))

    async def _run_with_retries(self, action_name: str, action, *, vendor_id: int):
        last_error: Exception | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return await asyncio.to_thread(action)
            except Exception as exc:
                last_error = exc
                if not self._is_transient_error(exc) or attempt == self.MAX_RETRIES:
                    raise
                delay = (0.25 * (2 ** (attempt - 1))) + random.uniform(0.0, 0.15)
                logger.warning(
                    "google_sheets_retry | vendor_id=%s | action=%s | attempt=%s | delay_seconds=%.2f",
                    vendor_id,
                    action_name,
                    attempt,
                    delay,
                )
                await asyncio.sleep(delay)
        if last_error:
            raise last_error

    @staticmethod
    def _http_status(exc: Exception) -> int | None:
        if isinstance(exc, HttpError):
            return getattr(getattr(exc, "resp", None), "status", None)
        return None

    @staticmethod
    def extract_spreadsheet_id(url_or_id: str) -> str:
        """Accepts a full Google Sheets URL, a /d/{id} path, or a bare id."""
        value = (url_or_id or "").strip()
        if not value:
            raise ValidationError("Spreadsheet URL is required")
        match = _SPREADSHEET_URL_RE.search(value)
        if match:
            return match.group(1)
        if _BARE_ID_RE.match(value):
            return value
        raise ValidationError(
            "Could not find a spreadsheet ID — paste the full URL from your browser's address bar"
        )

    # ------------------------------------------------------------ sync actions

    def _get_metadata_sync(self, credentials: Credentials, spreadsheet_id: str) -> dict:
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        return service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    async def validate_spreadsheet(self, vendor_id: int, url: str) -> dict:
        """Fetch sheet metadata to verify access before persisting the config."""
        spreadsheet_id = self.extract_spreadsheet_id(url)

        credentials = await self._get_credentials(vendor_id)
        if not credentials:
            raise ValidationError("Connect your Google account for Sheets first")

        try:
            metadata = await self._run_with_retries(
                "get_metadata",
                lambda: self._get_metadata_sync(credentials, spreadsheet_id),
                vendor_id=vendor_id,
            )
        except HttpError as exc:
            status = self._http_status(exc)
            if status in (403, 404):
                raise ValidationError(
                    "Spreadsheet not found or not shared with your connected Google account"
                ) from exc
            raise

        sheets = metadata.get("sheets") or []
        if not sheets:
            raise ValidationError("The spreadsheet has no tabs")

        tab_name = (sheets[0].get("properties") or {}).get("title") or "Sheet1"
        return {
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_title": metadata.get("properties", {}).get("title") or spreadsheet_id,
            "tab_name": tab_name,
        }

    def _read_column_a_sync(self, credentials: Credentials, spreadsheet_id: str, tab_name: str) -> list[list]:
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab_name}'!A:A",
        ).execute()
        return result.get("values") or []

    def _append_row_sync(
        self,
        credentials: Credentials,
        spreadsheet_id: str,
        tab_name: str,
        row: list[str],
    ) -> None:
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab_name}'!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

    def _first_cell_sync(self, credentials: Credentials, spreadsheet_id: str, tab_name: str) -> str | None:
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab_name}'!A1",
        ).execute()
        values = result.get("values") or []
        return values[0][0] if values and values[0] else None

    @staticmethod
    def _build_row(order: dict) -> list[str]:
        return [
            (order.get("created_at") or datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S")
            if not isinstance(order.get("created_at"), str)
            else order["created_at"],
            order.get("order_ref") or "",
            order.get("customer_name") or "",
            order.get("customer_phone") or "",
            order.get("customer_platform") or "",
            order.get("customer_handle") or "",
            order.get("order_details") or "",
            order.get("status") or "",
        ]

    async def sync_order(self, order: dict) -> bool:
        """Append one order row. Returns True when the row is (or now is) synced."""
        order_id = order["id"]
        vendor_id = order["vendor_id"]

        vendor_settings = await self.settings_repo.get(vendor_id)
        spreadsheet_id = vendor_settings.get("sheets_spreadsheet_id")
        if not vendor_settings.get("sheets_sync_enabled") or not spreadsheet_id:
            # Sync off (or not configured): leave the row pending; the sweep
            # picks it up if the vendor turns it back on.
            return False

        tab_name = vendor_settings.get("sheets_tab_name") or "Sheet1"

        credentials = await self._get_credentials(vendor_id)
        if not credentials:
            await self.orders.record_sync_failure(order_id, "reauth_needed", _SYNC_RETRY_BASE_SECONDS)
            return False

        try:
            # Duplicate guard — only on retries. Covers the case where an
            # append succeeded but the response was lost (network error).
            if order.get("sheets_sync_attempts", 0) > 0:
                existing = await self._run_with_retries(
                    "read_column_a",
                    lambda: self._read_column_a_sync(credentials, spreadsheet_id, tab_name),
                    vendor_id=vendor_id,
                )
                order_ref = order.get("order_ref")
                if any(row and row[0] == order_ref for row in existing):
                    logger.info("google_sheets_duplicate_guard_hit | order_id=%s", order_id)
                    await self.orders.mark_synced(order_id)
                    return True

            # Header row on the first write to an empty sheet.
            first_cell = await self._run_with_retries(
                "read_a1",
                lambda: self._first_cell_sync(credentials, spreadsheet_id, tab_name),
                vendor_id=vendor_id,
            )
            if not first_cell:
                await self._run_with_retries(
                    "append_header",
                    lambda: self._append_row_sync(credentials, spreadsheet_id, tab_name, _HEADER_ROW),
                    vendor_id=vendor_id,
                )

            row = self._build_row(order)
            await self._run_with_retries(
                "append_order_row",
                lambda: self._append_row_sync(credentials, spreadsheet_id, tab_name, row),
                vendor_id=vendor_id,
            )
            await self.orders.mark_synced(order_id)
            get_metrics_registry().increment("sheets_sync_success_total")
            logger.info("google_sheets_order_synced | order_id=%s | vendor_id=%s", order_id, vendor_id)
            return True
        except Exception as exc:
            attempts = int(order.get("sheets_sync_attempts", 0)) + 1
            status = self._http_status(exc)
            error = "spreadsheet_unavailable" if status in (403, 404) else f"sync_error: {exc}"
            retry_delay = min(_SYNC_RETRY_BASE_SECONDS * (2 ** max(attempts - 1, 0)), _SYNC_RETRY_MAX_SECONDS)
            await self.orders.record_sync_failure(order_id, error, retry_delay)
            get_metrics_registry().increment("sheets_sync_failures_total")
            logger.exception("google_sheets_order_sync_failed | order_id=%s | vendor_id=%s", order_id, vendor_id)
            return False

    async def sweep_pending(self, limit: int = 50) -> None:
        """Retry unsynced orders. Multi-worker safe via claim_pending."""
        try:
            claimed = await self.orders.claim_pending(limit=limit)
        except Exception:
            get_metrics_registry().increment("failures_total")
            logger.exception("google_sheets_sweep_claim_failed")
            return

        if not claimed:
            return

        logger.info("google_sheets_sweep_started | orders=%s", len(claimed))
        for order in claimed:
            try:
                await self.sync_order(order)
            except Exception:
                # One bad row must never kill the whole sweep.
                get_metrics_registry().increment("failures_total")
                logger.exception(
                    "google_sheets_sweep_order_error | order_id=%s", order.get("id")
                )
