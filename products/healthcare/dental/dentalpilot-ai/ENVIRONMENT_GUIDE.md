# Environment Variables

> **Moved.** The complete environment-variable reference is now in [`ENVIRONMENT.md`](ENVIRONMENT.md).

Quick reference:

- **Backend + worker (runtime):** `DATABASE_URL` (`postgresql+psycopg://`), `JWT_SECRET`, `APP_ENVIRONMENT`, `CORS_ORIGINS`; optional `XAI_*`, `RAZORPAY_*`, `S3_*`, `SMTP_*`, `WHATSAPP_*`.
- **Frontend (build-time):** `src/environments/environment.prod.ts` → `apiBaseUrl` (`https://api.dentalpilot.in/api/v1`).
- **Compose-only:** `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, `BACKEND_PORT`, `FRONTEND_PORT`, `REGISTRY`, `IMAGE_NAME`, `IMAGE_TAG`.

See [`ENVIRONMENT.md`](ENVIRONMENT.md) for the full table, build-time vs runtime classification, local vs production values and security guidance.