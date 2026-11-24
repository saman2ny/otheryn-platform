# Environment Variables

> **Consolidated.** The authoritative environment-variable reference is in [`docs/notion/SETUP_AND_DEPLOYMENT.md`](docs/notion/SETUP_AND_DEPLOYMENT.md).

It documents every backend/worker variable, Compose-only variables, build-time vs runtime classification, local/staging/production separation and secret-handling safety.

## Quick reference

- **Backend + worker (runtime):** `DATABASE_URL` (`postgresql+psycopg://`), `JWT_SECRET`, `APP_ENVIRONMENT`, `CORS_ORIGINS`, plus optional `XAI_*`, `RAZORPAY_*`, `S3_*`, `SMTP_*`, `WHATSAPP_*`.
- **Frontend (build-time):** `src/environments/environment.prod.ts` → `apiBaseUrl`.
- **Compose-only:** `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, `REDIS_PORT`, `BACKEND_PORT`, `REGISTRY`, `IMAGE_NAME`, `IMAGE_TAG`.

See [`docs/notion/SETUP_AND_DEPLOYMENT.md`](docs/notion/SETUP_AND_DEPLOYMENT.md) for the full table.