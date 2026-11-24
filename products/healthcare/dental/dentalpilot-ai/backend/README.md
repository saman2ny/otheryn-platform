# DentalPilot AI — Backend

FastAPI REST API with background workers. This is a **concise component guide**; the authoritative architecture is in [`../docs/notion/TECHNICAL_ARCHITECTURE.md`](../docs/notion/TECHNICAL_ARCHITECTURE.md) and the full setup/deployment is in [`../docs/notion/SETUP_AND_DEPLOYMENT.md`](../docs/notion/SETUP_AND_DEPLOYMENT.md).

## Stack

- FastAPI `0.139.2`, Pydantic `2.13.4`, Uvicorn `0.51.0`.
- SQLAlchemy `2.0.51`, Alembic `1.18.5`.
- Python **3.12** (Docker); Railway Nixpacks uses `python311` (mismatch — see architecture doc).
- PostgreSQL 16 (production) / SQLite (native default); `postgresql+psycopg://` for Postgres.
- bcrypt `5.0.0`, PyJWT `2.13.0`, OpenAI SDK (xAI-compatible), Razorpay `2.0.1`, boto3.
- Tested locally on Python 3.12 (Docker `python:3.12-slim`). Railway deploys with Nixpacks `python311` (3.11) — a known mismatch; recommended to align on 3.12.

## Commands

```bash
cd products/healthcare/dental/dentalpilot-ai/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: JWT_SECRET, DATABASE_URL, CORS_ORIGINS

alembic upgrade head
python scripts/seed_hierarchy.py
uvicorn app.main:app --reload --reload-dir app --port 8000

pytest tests/ -q
```

- Swagger: <http://localhost:8000/docs>
- Health: `/health`, `/health/live`, `/health/ready`
- API base: `http://localhost:8000/api/v1`

## Architecture

```
app/
├── main.py          # FastAPI app, middleware, routers, health
├── core/
│   ├── config.py    # pydantic-settings (env vars)
│   ├── database.py  # engine, SessionLocal, get_db
│   ├── deps.py      # CurrentUser, CurrentPatient, RequireOwner, RequireSuperAdmin
│   └── security.py  # bcrypt, JWT create/decode
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response (CamelModel)
├── routers/         # 16 routers, ~156 endpoints
├── services/        # ai_content, razorpay, document_storage, email_delivery, export_render, integration_adapters
└── workers/         # run_workers, email_outbox, communication_outbox, subscription_billing
```

**Critical:** `CatchAllExceptionMiddleware` must be registered **before** `CORSMiddleware`. Error format: `{ statusCode, message, errors? }`.

## API summary

All routes are prefixed `/api/v1`. Key groups:

- `/auth` — register/login/refresh/logout/forgot-password/me.
- `/clinic` — profile, branches, staff, onboarding, AI settings.
- `/healthcare` — patients, enquiries, visits, treatment plans/stages, ledger, claims, records, consents, reminders, recall, email outbox, audit, CSV import/export.
- `/analytics` — revenue, financial summary, treatment follow-up, retention, operational.
- `/operations` — dental cases, assets, maintenance, sterilisation, drafts, note review.
- `/organizations` — organizations, members, invitations, analytics.
- `/patient-portal` — invitations, login, records, shares, downloads.
- `/billing` — subscriptions, invoices, treatment payments, webhooks, accounting CSV, PMS reconciliation.
- `/content`, `/calendar/events`, `/export`, `/growth`, `/integrations`, `/dashboard`, `/admin`.

Full endpoint reference: [`TECHNICAL_ARCHITECTURE.md`](../docs/notion/TECHNICAL_ARCHITECTURE.md).

## Background workers

```bash
python -m app.workers.run_workers
```

Three loops: `email_outbox`, `communication_outbox`, `subscription_billing`. They are **database-backed**; **Redis is not used**. Do not run multiple workers against the same database. The worker does not run migrations.

## Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic current
alembic history
```

**Known SQLite issue:** `alembic upgrade head` on SQLite fails at `e78cbd0fad9c` (`Constraint must have a name`). Use PostgreSQL for a reliable local setup.

## Production deployment (summary)

Railway backend: root `backend/`, Nixpacks (`railway.toml`), start `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health `/health`. Worker: separate service, start `python -m app.workers.run_workers`. `DATABASE_URL` must be `postgresql+psycopg://`.

Full steps, env vars and troubleshooting: [`../docs/notion/SETUP_AND_DEPLOYMENT.md`](../docs/notion/SETUP_AND_DEPLOYMENT.md).

## Links

- [`../README.md`](../README.md) — project entry point.
- [`../docs/notion/SETUP_AND_DEPLOYMENT.md`](../docs/notion/SETUP_AND_DEPLOYMENT.md) — local + production.
- [`../docs/notion/TECHNICAL_ARCHITECTURE.md`](../docs/notion/TECHNICAL_ARCHITECTURE.md) — architecture/API/DB.
- [`../docs/notion/BUSINESS_PROPOSAL.md`](../docs/notion/BUSINESS_PROPOSAL.md) — business.
- [`../RELEASE_NOTES.md`](../RELEASE_NOTES.md) — release history.