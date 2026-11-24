# DentalPilot AI — Environment & Configuration Guide

This document owns **environment variable** and **configuration** documentation for DentalPilot AI. It explains what each variable does, which service uses it, and how local, staging and production differ.

> For local setup and hot reload, see [`LOCAL_DEVELOPMENT.md`](LOCAL_DEVELOPMENT.md). For production deployment, see [`RAILWAY_DEPLOYMENT.md`](RAILWAY_DEPLOYMENT.md).

---

## 1. Environment overview

| Environment | Where it runs | Database | Secrets | Config source |
|---|---|---|---|---|
| **Local** | Your machine (Docker Compose or native) | PostgreSQL 16 (Docker) or SQLite | Local-only values | `.env.local` (Docker) or `backend/.env` (native) |
| **Staging** | Docker Compose on a staging host | PostgreSQL 16 (Compose volume) | Staging-only values | `.env.staging` |
| **Production** | Railway | Railway PostgreSQL | Railway variables | Railway service variables |

**Local, staging and production data are separate.** A local `.env` must never contain production credentials, and a local `DATABASE_URL` must never point at a production database.

```mermaid
flowchart LR
    subgraph LOCAL["LOCAL"]
      LFE[ng serve :4200] --> LAPI[FastAPI :8000]
      LAPI --> LPG[(Local Postgres)]
      LW[Workers] --> LPG
    end
    subgraph PROD["PRODUCTION (Railway)"]
      PFE[Nginx + Angular] --> PAPI[FastAPI]
      PAPI --> PPG[(Railway Postgres)]
      PW[Worker] --> PPG
    end
    LOCAL -. "git push only" .-> PROD
```

---

## 2. Build-time vs runtime configuration

| Component | Configuration source | When applied | How to change |
|---|---|---|---|
| **Angular frontend** | `src/environments/environment.prod.ts` | **Build time** (compiled into the JS bundle by `angular.json` `fileReplacements`) | Edit the file and **rebuild** |
| **FastAPI backend** | `app/core/config.py` via environment variables | **Runtime** (read on startup) | Change the variable and **restart/redeploy** |
| **Workers** | Same as backend | **Runtime** | Change the variable and **restart** |
| **Nginx** | `frontend/nginx.conf` (baked) or mounted config | **Runtime** (container start) | Rebuild the image or mount a config |

Railway environment variables do **not** affect the Angular bundle. The frontend API URL is set in `src/environments/environment.prod.ts`:

```ts
export const environment = {
  production: true,
  apiBaseUrl: 'https://api.dentalpilot.in/api/v1',
};
```

---

## 3. Core environment variables

| Variable | Service | Required | Purpose | Local example | Production example | Setting |
|---|---|---|---|
| `APP_ENVIRONMENT` | backend, worker | ✅ | Environment mode (`development`/`test`/`staging`/`production`) | `development` | `production` | runtime |
| `DATABASE_URL` | backend, worker | ✅ | SQLAlchemy connection string | `postgresql+psycopg://dentalpilot:local@postgres:5432/dentalpilot` | `postgresql+psycopg://…` | runtime |
| `JWT_SECRET` | backend, worker | ✅ | JWT signing secret (32+ chars in production) | `local-dev-secret` | `<openssl rand -base64 48>` | runtime |
| `JWT_ALGORITHM` | backend, worker | optional | JWT algorithm | `HS256` | `HS256` | runtime |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | backend | optional | Access token lifetime | `30` | `30` | runtime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | backend | optional | Refresh token lifetime | `30` | `30` | runtime |
| `CORS_ORIGINS` | backend | ✅ in prod | Allowed frontend origins (JSON array) | `["http://localhost:4200"]` | `["https://dentalpilot.in"]` | runtime |
| `MAX_PATIENT_DOCUMENT_BYTES` | backend, worker | optional | Upload size limit (bytes) | `25000000` | `25000000` | runtime |

> **`DATABASE_URL` must use `postgresql+psycopg://`** — the `psycopg` 3 driver is installed, not `psycopg2`. Railway's `${{Postgres.DATABASE_URL}}` is `postgresql://…`; convert it.

### Production validation

`app/core/config.py` enforces in production:
- `JWT_SECRET` is non-default and ≥32 characters.
- `DATABASE_URL` is **not** SQLite.
- `CORS_ORIGINS` does not contain `*`.
- If Razorpay keys are set, `RAZORPAY_WEBHOOK_SECRET` and all paid tier/cycle plan IDs must be present.

---

## 4. Integration variables (all optional)

Disabled integrations fail gracefully (endpoints return `503`) — the app still starts.

| Variable | Service | Purpose | Notes |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | backend, worker | Anthropic AI | Empty disables AI content |
| `ANTHROPIC_MODEL` | backend, worker | Model name | Default `claude-opus-4-8` |
| `CLINICAL_NOTE_DRAFTING_ENABLED` | backend | Enable AI note drafting | Requires `CLINICAL_AI_DATA_PROCESSING_APPROVED=true` |
| `CLINICAL_AI_DATA_PROCESSING_APPROVED` | backend | Consent gate for AI notes | Must be explicitly true |
| `RAZORPAY_KEY_ID` | backend, worker | Razorpay key | Set with secret |
| `RAZORPAY_KEY_SECRET` | backend, worker | Razorpay secret | Set with key |
| `RAZORPAY_WEBHOOK_SECRET` | backend, worker | Webhook signature verification | Required with Razorpay in production |
| `RAZORPAY_CURRENCY` | backend, worker | Subscription currency | Default `INR` |
| `RAZORPAY_PLAN_IDS` | backend, worker | Tier/cycle → plan IDs (JSON) | Required with Razorpay in production |
| `PATIENT_PAYMENT_CURRENCY` | backend, worker | Treatment payment currency | Default `INR` |
| `S3_BUCKET` | backend, worker | Document storage bucket | Empty disables uploads |
| `S3_ENDPOINT_URL` | backend, worker | S3-compatible endpoint | Optional (AWS default) |
| `AWS_REGION` | backend, worker | AWS region | Default `us-east-1` |
| `S3_KMS_KEY_ID` | backend, worker | KMS key for SSE | Optional |
| `SMTP_HOST` | backend, worker | SMTP server | Empty disables email |
| `SMTP_PORT` | backend, worker | SMTP port | Default `587` |
| `SMTP_USERNAME` | backend, worker | SMTP user | |
| `SMTP_PASSWORD` | backend, worker | SMTP password | |
| `SMTP_SENDER_EMAIL` | backend, worker | Sender address | |
| `SMTP_SENDER_NAME` | backend, worker | Sender name | Default `DentalPilot AI` |
| `SMTP_USE_SSL` | backend, worker | Implicit SSL | Default `false` |
| `SMTP_USE_STARTTLS` | backend, worker | STARTTLS | Default `true` |
| `EMAIL_WORKER_INTERVAL_SECONDS` | worker | Email poll interval | Default `10` |
| `EMAIL_MAX_ATTEMPTS` | worker | Email retry cap | Default `5` |
| `WHATSAPP_PHONE_NUMBER_ID` | backend, worker | WhatsApp sender ID | |
| `WHATSAPP_ACCESS_TOKEN` | backend, worker | WhatsApp token | |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | backend, worker | Webhook verification | |
| `SUBSCRIPTION_GRACE_PERIOD_DAYS` | worker | Grace period | Default `7` |
| `BILLING_WEBHOOK_INTERVAL_SECONDS` | worker | Billing poll interval | Default `5` |
| `BILLING_WEBHOOK_MAX_ATTEMPTS` | worker | Billing retry cap | Default `10` |
| `SUBSCRIPTION_RECONCILIATION_INTERVAL_SECONDS` | worker | Reconciliation interval | Default `3600` |

> **Redis is not used by application code.** `REDIS_HOST`/`REDIS_PORT` are passed by Docker Compose but no Redis client is installed or imported. The workers are PostgreSQL-backed.

---

## 5. Compose-only variables (not app config)

These are used by `docker-compose.yml` / `docker-compose.local.yml`, not by `app/core/config.py`:

| Variable | Used by | Purpose |
|---|---|---|
| `POSTGRES_USER` | Postgres container, backend DATABASE_URL | DB user |
| `POSTGRES_PASSWORD` | Postgres container, backend DATABASE_URL | DB password |
| `POSTGRES_DB` | Postgres container, backend DATABASE_URL | DB name |
| `POSTGRES_PORT` | local Compose | Host port for Postgres |
| `REDIS_PORT` | local Compose | Host port for Redis (unused by app) |
| `BACKEND_PORT` | local Compose | Host port for FastAPI |
| `REGISTRY` | production Compose | Image registry (e.g. `ghcr.io`) |
| `IMAGE_NAME` | production Compose | Image name |
| `IMAGE_TAG` | production Compose | Immutable tag (e.g. `sha-<commit>`) |

---

## 6. Local configuration

- **Docker (recommended):** copy `.env.local.example` to `.env.local`, set `POSTGRES_PASSWORD`, `JWT_SECRET`, and `DATABASE_URL` (host `postgres`).
- **Native:** copy `backend/.env.example` to `backend/.env`, set `JWT_SECRET` and `DATABASE_URL` (SQLite or Postgres).

Full commands, hot reload, startup/shutdown and troubleshooting: [`LOCAL_DEVELOPMENT.md`](LOCAL_DEVELOPMENT.md).

## 7. Staging configuration

Copy `.env.staging.example` to `.env.staging`, set staging-only credentials, and run:

```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

Staging uses HTTP-only Nginx on port `8080` and staging CORS origins. It must never reuse production secrets.

## 8. Production configuration (Railway)

Set variables in Railway → service → **Variables**:

- **Backend + worker:** `DATABASE_URL`, `JWT_SECRET`, `APP_ENVIRONMENT=production`, `CORS_ORIGINS`, plus optional integrations.
- **Frontend:** none at runtime; the API URL is build-time in `environment.prod.ts`.

Full service-by-service instructions: [`RAILWAY_DEPLOYMENT.md`](RAILWAY_DEPLOYMENT.md).

---

## 9. Data separation and safety

### 9.1 Where data lives

| Environment | Database | Location |
|---|---|---|
| Local Docker | PostgreSQL 16 | Docker volume `dentalpilot-local_postgres_data` |
| Local native | SQLite | `backend/dentalpilot.db` |
| Staging Compose | PostgreSQL 16 | Docker volume `dentalpilot_postgres_data` |
| Production | Railway PostgreSQL | Railway-managed |

### 9.2 Never do these

- ❌ Put production `DATABASE_URL`, `JWT_SECRET` or API keys in `.env`, `.env.local` or `.env.staging`.
- ❌ Point a local backend at a production Postgres host.
- ❌ Run `docker compose ... down -v` against a staging/production Compose project.
- ❌ Run `alembic downgrade` or `DROP`/`TRUNCATE` against production.
- ❌ Commit `.env*` files (the root `.gitignore` ignores them).

### 9.3 Verify which database you are connected to

```bash
# Native backend (venv active)
python -c "from app.core.config import settings; from urllib.parse import urlparse; u=urlparse(settings.database_url); print('host=', u.hostname, 'db=', u.path)"

# Docker Compose backend
docker compose -f docker-compose.local.yml exec backend python -c "from app.core.config import settings; from urllib.parse import urlparse; u=urlparse(settings.database_url); print('host=', u.hostname, 'db=', u.path)"

# Railway backend
railway run python -c "from app.core.config import settings; from urllib.parse import urlparse; u=urlparse(settings.database_url); print('host=', u.hostname, 'db=', u.path)"
```

Expected:

- Local Docker: `host= postgres db= /dentalpilot`
- Local native: `host= None db= ./dentalpilot.db`
- Production: `host= <railway-postgres-host> db= /railway`

### 9.4 Switching safely

**Local → production:** commit + push; Railway builds. Local env changes never affect production.

**Before any production deploy:**

1. `railway status` — confirm the correct project/service.
2. `railway variables` — confirm `APP_ENVIRONMENT=production`, non-SQLite `DATABASE_URL`, `JWT_SECRET` set.
3. Run tests locally (`pytest`, `npm test`).
4. Use backward-compatible migrations.
5. Deploy, then `curl /health/ready`.
6. Keep the previous deployment for rollback.

---

## 10. Troubleshooting

| Symptom | Check |
|---|---|
| Local API cannot reach DB | `docker compose ... ps`; `DATABASE_URL` host must be `postgres` |
| Local frontend cannot reach API | Backend on `:8000`; `CORS_ORIGINS` includes `http://localhost:4200` |
| Production 500 on startup | `railway logs`; usually `DATABASE_URL` scheme or missing `JWT_SECRET` |
| Production `psycopg2` error | `DATABASE_URL` must be `postgresql+psycopg://` |
| Production migrations failed | `railway logs`; fix migration; redeploy |
| Worker not sending | Check worker logs; SMTP/WhatsApp vars set |
| Deployed commit is old | Railway → Deployments → Details → SHA |

---

## 11. Related documentation

- [`README.md`](README.md) — overview and quick start.
- [`LOCAL_DEVELOPMENT.md`](LOCAL_DEVELOPMENT.md) — full local setup and hot reload.
- [`RAILWAY_DEPLOYMENT.md`](RAILWAY_DEPLOYMENT.md) — production deployment.
- [`backend/README.md`](backend/README.md) — backend/worker details.
- [`frontend/README.md`](frontend/README.md) — Angular details.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution workflow.