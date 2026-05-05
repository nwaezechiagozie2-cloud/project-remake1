# One-Tap Closer Remake

Production-oriented remake of One-Tap Closer, rebuilt with modular boundaries and explicit contracts.

## What this includes

- FastAPI backend with clean routing, service layer, and repository layer
- Async SQLAlchemy persistence (works with SQLite for local dev and MySQL in production)
- Webhook ingestion and event parsing for WhatsApp Cloud API
- Human-in-the-loop purchase approval flow with explicit vendor confirmation gate
- Vendor auth (register/login) with JWT
- Vendor admin API for products, bot settings, and catalogue assets
- Google OAuth routes for vendor contact-sync integration

## Project layout

```text
project remake/
├── alembic/
│   ├── env.py
│   └── versions/
├── alembic.ini
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   ├── domain/
│   │   ├── interfaces.py
│   │   └── models.py
│   ├── repositories/
│   │   ├── base.py
│   │   ├── models.py
│   │   └── sql.py
│   ├── schemas/
│   │   └── api.py
│   ├── services/
│   │   ├── agent_service.py
│   │   ├── auth_service.py
│   │   ├── google_contacts_service.py
│   │   ├── llm_service.py
│   │   ├── webhook_service.py
│   │   └── whatsapp_service.py
│   ├── config.py
│   ├── logging.py
│   └── main.py
├── scripts/
│   ├── seed_qa_data.py
│   └── smoke_test.py
├── tests/
│   └── test_health.py
├── .env.example
└── requirements.txt
```

## Local run

```bash
cd "project remake"
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8001/health
```

## Quick validation

```bash
pytest -q tests
python scripts/smoke_test.py
```

## Database migrations (Alembic)

Create / apply migrations:

```bash
cd "project remake"
python -m alembic -c alembic.ini upgrade head
```

Rollback one step:

```bash
cd "project remake"
python -m alembic -c alembic.ini downgrade -1
```

Reset and re-apply from scratch:

```bash
cd "project remake"
python -m alembic -c alembic.ini downgrade base
python -m alembic -c alembic.ini upgrade head
```

## Local QA seed data

Populate realistic local QA records (vendor, products, customer, conversation, messages, token):

```bash
cd "project remake"
python scripts/seed_qa_data.py
```

## Production notes

- Set `DATABASE_URL` to a managed MySQL DSN in production.
- Set `JWT_SECRET` to a long random value.
- Populate WhatsApp vendor credentials per vendor record.
- Configure Google OAuth credentials before enabling contact sync.
- Completed OAuth callback stores per-vendor credentials in `vendor_google_tokens`.
- Add migrations (Alembic) before production rollout.

## Production runbook

Environment essentials:

- `APP_ENV=production`
- `DATABASE_URL` points to production MySQL
- `JWT_SECRET` is high-entropy (startup guard enforces minimum length)
- `WHATSAPP_APP_SECRET` set to enable webhook signature verification
- Google OAuth settings (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`) configured when contacts sync is enabled

Startup sequence:

```bash
cd "project remake"
python -m alembic -c alembic.ini upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Readiness + telemetry checks:

```bash
curl -s http://127.0.0.1:8001/health
curl -s http://127.0.0.1:8001/ready
curl -s http://127.0.0.1:8001/metrics
```

Rollback:

```bash
cd "project remake"
python -m alembic -c alembic.ini downgrade -1
```

Smoke checks after deploy:

```bash
cd "project remake"
python scripts/smoke_test.py
```
