# DentalPilot AI — Environment Variables

**Audience:** developers, DevOps/platform engineers.
**Scope:** the complete environment-variable reference. Local setup is in [`docs/notion/SETUP_AND_DEPLOYMENT.md`](docs/notion/SETUP_AND_DEPLOYMENT.md). Production deployment is in [`DEPLOYMENT.md`](DEPLOYMENT.md).

> **Never commit real secrets.** `.env`, `.env.local`, `.env.production`, `.env.staging` are gitignored. Use Railway variables or a protected deployment secret store.

---

## 1. Build-time vs runtime

| Component | Configuration source | When applied | How to change |
|---|---|---|---|
| **Angular frontend** | `frontend/src/environments/environment.prod.ts` | **Build time** (compiled by `angular.json` `fileReplacements`) | Edit the file and **rebuild** |
| **FastAPI backend** | `app/core/config.py` via environment variables | **Runtime** (on startup) | Change the variable and **restart/redeploy** |
| **Workers** | Same as backend | **Runtime** | Change the variable and **restart** |
| **Nginx** | `frontend/nginx.conf` / `nginx/conf.d` | **Runtime** (container start) | Rebuild the image or mount a config |

Railway variables do **not** affect the Angular bundle. The frontend API URL is set in `src/environments/environment.prod.ts`:

```ts
export const environment = {
  production: true,
  apiBaseUrl: 'https://api.dentalpilot.in/api/v1',
};
```

---

## 2. Core variables

| Variable | Service | Required | Purpose | Local / Production | Setting |
|---|---|---|---|---|---|
| `APP_ENVIRONMENT` | backend, worker | ✅ | `development` / `test` / `staging` / `production` | both | runtime |
| `DATABASE_URL` | backend, worker | ✅ | SQLAlchemy URL (`postgresql+psycopg://`) | both | runtime |
| `JWT_SECRET` | backend, worker | ✅ | JWT signing (32+ chars in production) | both | runtime |
| `JWT_ALGORITHM` | backend, worker | optional | JWT algorithm | both | runtime |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | backend | optional | Access token lifetime | both | runtime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | backend | optional | Refresh token lifetime | both | runtime |
| `CORS_ORIGINS` | backend | ✅ in prod | Allowed origins (JSON array) | both | runtime |
| `MAX_PATIENT_DOCUMENT_BYTES` | backend, worker | optional | Upload size limit | both | runtime |

> **`DATABASE_URL` must use `postgresql+psycopg://`.** Railway's `${{Postgres.DATABASE_URL}}` is `postgresql://...`; SQLAlchemy would try `psycopg2`, which is **not installed**.

---

## 3. Integration variables (all optional)

Disabled integrations fail gracefully (`503`) — the app still starts.

| Variable | Service | Purpose | Local | Production |
|---|---|---|---|---|
| `XAI_API_KEY` | backend, worker | xAI Grok API key | optional | optional |
| `XAI_MODEL` | backend, worker | Grok model (`grok-4.7`) | optional | optional |
| `XAI_BASE_URL` | backend, worker | xAI API base (`https://api.x.ai/v1`) | optional | optional |
| `CLINICAL_NOTE_DRAFTING_ENABLED` | backend | Enable AI note drafting | optional | optional |
| `CLINICAL_AI_DATA_PROCESSING_APPROVED` | backend | Consent gate for AI notes | optional | optional |
| `RAZORPAY_KEY_ID` | backend, worker | Razorpay key | optional | optional |
| `RAZORPAY_KEY_SECRET` | backend, worker | Razorpay secret | optional | optional |
| `RAZORPAY_WEBHOOK_SECRET` | backend, worker | Webhook verification | optional | required with Razorpay |
| `RAZORPAY_CURRENCY` | backend, worker | Subscription currency | optional | optional |
| `RAZORPAY_PLAN_IDS` | backend, worker | Tier/cycle → plan IDs (JSON) | optional | required with Razorpay |
| `PATIENT_PAYMENT_CURRENCY` | backend, worker | Treatment payment currency | optional | optional |
| `S3_BUCKET` | backend, worker | Document bucket | optional | optional |
| `S3_ENDPOINT_URL` | backend, worker | S3-compatible endpoint | optional | optional |
| `AWS_REGION` | backend, worker | AWS region | optional | optional |
| `S3_KMS_KEY_ID` | backend, worker | KMS key for SSE | optional | optional |
| `SMTP_HOST` | backend, worker | SMTP server | optional | optional |
| `SMTP_PORT` | backend, worker | SMTP port | optional | optional |
| `SMTP_USERNAME` | backend, worker | SMTP user | optional | optional |
| `SMTP_PASSWORD` | backend, worker | SMTP password | optional | optional |
| `SMTP_SENDER_EMAIL` | backend, worker | Sender address | optional | optional |
| `SMTP_SENDER_NAME` | backend, worker | Sender name | optional | optional |
| `SMTP_USE_SSL` | backend, worker | Implicit SSL | optional | optional |
| `SMTP_USE_STARTTLS` | backend, worker | STARTTLS | optional | optional |
| `EMAIL_WORKER_INTERVAL_SECONDS` | worker | Email poll interval | optional | optional |
| `EMAIL_MAX_ATTEMPTS` | worker | Email retry cap | optional | optional |
| `WHATSAPP_PHONE_NUMBER_ID` | backend, worker | WhatsApp sender ID | optional | optional |
| `WHATSAPP_ACCESS_TOKEN` | backend, worker | WhatsApp token | optional | optional |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | backend, worker | WhatsApp webhook verification | optional | optional |
| `SUBSCRIPTION_GRACE_PERIOD_DAYS` | worker | Grace period | optional | optional |
| `BILLING_WEBHOOK_INTERVAL_SECONDS` | worker | Billing poll interval | optional | optional |
| `BILLING_WEBHOOK_MAX_ATTEMPTS` | worker | Billing retry cap | optional | optional |
| `SUBSCRIPTION_RECONCILIATION_INTERVAL_SECONDS` | worker | Reconciliation interval | optional | optional |

**Redis is not used by application code.** Do not add Redis variables unless you implement a Redis-backed feature.

---

## 4. Compose-only variables

Used by `docker-compose.yml` / `docker-compose.local.yml`, not by `app/core/config.py`:

| Variable | Used by | Purpose |
|---|---|---|
| `POSTGRES_USER` | Postgres container, backend `DATABASE_URL` | DB user |
| `POSTGRES_PASSWORD` | Postgres container, backend `DATABASE_URL` | DB password |
| `POSTGRES_DB` | Postgres container, backend `DATABASE_URL` | DB name |
| `POSTGRES_PORT` | local Compose | Host port for Postgres |
| `BACKEND_PORT` | local Compose | Host port for FastAPI |
| `FRONTEND_PORT` | local Compose | Host port for Angular |
| `REGISTRY` | production Compose | Image registry (e.g. `ghcr.io`) |
| `IMAGE_NAME` | production Compose | Image name |
| `IMAGE_TAG` | production Compose | Immutable tag (e.g. `sha-<commit>`) |

---

## 5. Local vs production

| Variable | Local (`docker-compose.local.yml`) | Production (Railway / Compose) |
|---|---|---|
| `APP_ENVIRONMENT` | `development` | `production` |
| `DATABASE_URL` | `postgresql+psycopg://...@postgres:5432/...` | `postgresql+psycopg://...` (Railway Postgres) |
| `JWT_SECRET` | local-only random | 32+ random |
| `CORS_ORIGINS` | `["http://localhost:4200"]` | `["https://dentalpilot.in"]` |
| `XAI_*` / `RAZORPAY_*` / `S3_*` / `SMTP_*` | optional/empty | production values |
| `POSTGRES_*` | local Compose | not used (Railway Postgres) |
| `REGISTRY` / `IMAGE_NAME` / `IMAGE_TAG` | not used | production Compose |

**Never point a local `.env` at a production database.**

---

## 6. Verification

```bash
# Native backend (venv active) — only for non-Docker development
python -c "from app.core.config import settings; from urllib.parse import urlparse; u=urlparse(settings.database_url); print('host=', u.hostname, 'db=', u.path)"

# Docker Compose backend
docker compose -f docker-compose.local.yml exec backend python -c "from app.core.config import settings; from urllib.parse import urlparse; u=urlparse(settings.database_url); print('host=', u.hostname, 'db=', u.path)"

# Railway backend
railway run python -c "from app.core.config import settings; from urllib.parse import urlparse; u=urlparse(settings.database_url); print('host=', u.hostname, 'db=', u.path)"
```

Expected:

- Local Docker: `host= postgres db= /dentalpilot`
- Production: `host= <railway-postgres-host> db= /railway`

---

## 7. Security

- Never commit `.env*` files.
- Use Railway variables or a secret manager.
- Production `JWT_SECRET` ≥32 chars; `DATABASE_URL` non-SQLite; no `*` CORS.
- Keep `RAZORPAY_WEBHOOK_SECRET` private.
- S3 bucket private; SSE/KMS.
- Do not log secrets or patient data.

---

## Related documentation

- [`docs/notion/SETUP_AND_DEPLOYMENT.md`](docs/notion/SETUP_AND_DEPLOYMENT.md) — local Docker development.
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — production deployment.
- [`docs/notion/TECHNICAL_ARCHITECTURE.md`](docs/notion/TECHNICAL_ARCHITECTURE.md) — architecture.
- [`ENVIRONMENT_GUIDE.md`](ENVIRONMENT_GUIDE.md) — pointer to this document.