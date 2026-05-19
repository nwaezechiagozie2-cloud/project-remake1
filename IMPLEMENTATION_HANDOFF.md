# Implementation Handoff

This file summarizes the backend changes made so a new chat can continue from the current project state.

## Main Changes

### 1. Removed `vendor_knowledge_entries` From Runtime Code

The old `vendor_knowledge_entries` table is no longer used by the app because `vendor_business_info` now covers that purpose.

Changed files:
- `app/repositories/models.py`
- `app/repositories/sql.py`
- `app/domain/interfaces.py`
- `app/api/deps.py`
- `app/api/routes/vendor_admin.py`
- `app/services/agent_service.py`
- `app/agent/agent.py`
- `app/agent/tools.py`
- `app/schemas/api.py`

Migration added:
- `alembic/versions/20260519_01_catalogue_ingestion_cleanup.py`

What the migration does:
- Copies existing `vendor_knowledge_entries.answer` rows into `vendor_business_info`.
- Marks copied rows with `source_type = 'MIGRATED_KNOWLEDGE'`.
- Drops the old `vendor_knowledge_entries` table.

## 2. Product Availability Toggle Per Product

Products already had an `in_stock` field. I added a clearer endpoint specifically for toggling availability.

Endpoint:

```http
PATCH /vendors/{vendor_id}/products/{product_id}/availability
```

Request body:

```json
{
  "in_stock": false
}
```

Changed files:
- `app/api/routes/vendor_admin.py`
- `app/schemas/api.py`

Existing generic product update still works too:

```http
PATCH /vendors/{vendor_id}/products/{product_id}
```

with:

```json
{
  "in_stock": true
}
```

## 3. Vendor-Level “Use Product Availability” Setting

Added a vendor bot setting so the vendor can decide whether the agent should care about product availability at all.

New setting:

```json
{
  "use_product_availability": true
}
```

Endpoint:

```http
PUT /vendors/{vendor_id}/bot-settings
```

Behavior:
- `use_product_availability: true`: agent sees `Available` / `Not available`.
- `use_product_availability: false`: agent does not see stock status and can continue selling without knowing availability.

Changed files:
- `app/repositories/models.py`
- `app/repositories/sql.py`
- `app/schemas/api.py`
- `app/agent/tools.py`

Migration added:
- `alembic/versions/20260519_02_product_availability_setting.py`

## 4. Agent Product Search Now Includes Availability Conditionally

The `search_products` tool now checks vendor settings.

File:
- `app/agent/tools.py`

Logic:
- If `use_product_availability` is true, product search output includes availability.
- If false, product search output hides availability.

This means the agent behavior changes without needing to delete or ignore the actual `products.in_stock` column.

## 5. Catalogue Ingestion Design and Backend Foundation

Added a staged catalogue ingestion flow.

The goal is:
1. Vendor uploads catalogue text/PDF/DOCX content.
2. Backend extracts text.
3. Extracted text is saved.
4. Extracted text is also added to `vendor_business_info` so the AI can search it.
5. Backend parses possible products into draft import items.
6. Vendor/admin can review and import selected draft items into real `products`.

New tables:
- `vendor_catalogue_uploads`
- `catalogue_import_items`

Migration:
- `alembic/versions/20260519_01_catalogue_ingestion_cleanup.py`

New service:
- `app/services/catalogue_ingestion_service.py`

New dependencies:
- `pypdf`
- `python-docx`

Updated file:
- `requirements.txt`

## 6. Catalogue Endpoints

Upload catalogue as base64:

```http
POST /vendors/{vendor_id}/catalogue/uploads
```

Request body:

```json
{
  "file_name": "catalogue.pdf",
  "mime_type": "application/pdf",
  "content_base64": "<base64-file-content>"
}
```

List uploads:

```http
GET /vendors/{vendor_id}/catalogue/uploads
```

List parsed draft products for an upload:

```http
GET /vendors/{vendor_id}/catalogue/uploads/{upload_id}/items
```

Import one parsed draft item as a real product:

```http
POST /vendors/{vendor_id}/catalogue/items/{item_id}/import
```

Changed files:
- `app/api/routes/vendor_admin.py`
- `app/schemas/api.py`
- `app/repositories/models.py`
- `app/repositories/sql.py`
- `app/domain/interfaces.py`

## Important Design Decision

Catalogue parsing does not automatically create products.

It creates draft `catalogue_import_items` first. This avoids bad parsing from a PDF/DOCX polluting the real `products` table. The vendor/admin imports only the items they approve.

## Commands To Run

Install new dependencies:

```bash
venv/bin/pip install -r requirements.txt
```

Run migrations:

```bash
venv/bin/alembic upgrade head
```

Current Alembic head after these changes:

```text
20260519_02
```

## Verification Already Done

These passed:

```bash
venv/bin/python -m compileall app
venv/bin/python -c "from app.main import app; print(app.title)"
venv/bin/alembic heads
```

Notes:
- `python -m compileall app` outside the venv failed earlier because global Python did not have FastAPI installed. Use `venv/bin/python`.
- `alembic` outside the venv was not found. Use `venv/bin/alembic`.

## Known Next Steps

Frontend/admin UI should add:
- A per-product availability toggle calling:
  - `PATCH /vendors/{vendor_id}/products/{product_id}/availability`
- A vendor-level “Use product availability” switch calling:
  - `PUT /vendors/{vendor_id}/bot-settings`
- Catalogue upload screen calling:
  - `POST /vendors/{vendor_id}/catalogue/uploads`
- Catalogue review screen showing:
  - `GET /vendors/{vendor_id}/catalogue/uploads/{upload_id}/items`
- Import button for each parsed item:
  - `POST /vendors/{vendor_id}/catalogue/items/{item_id}/import`

## Git/Workspace Note

The worktree already had many unrelated modified/untracked files before and during these changes. Do not blindly reset the repo.
