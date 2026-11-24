# Railway Deployment

> **Moved.** The complete production deployment guide — Railway **and** Docker Compose VPS — is now in [`DEPLOYMENT.md`](DEPLOYMENT.md).

Quick reference:

| Service | Root | Build | Start |
|---|---|---|---|
| Backend | `products/healthcare/dental/dentalpilot-ai/backend` | Nixpacks (`railway.toml`) | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Worker | same | same | `python -m app.workers.run_workers` |
| Frontend | `products/healthcare/dental/dentalpilot-ai/frontend` | Dockerfile (`node:20-alpine` → `nginx:alpine`) | Nginx |
| PostgreSQL | Railway-managed | — | — |

**Critical:** `DATABASE_URL` must use `postgresql+psycopg://`. **No Uvicorn `--reload` in production.** **Redis is not used.**

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for the full procedure: domains, TLS, migrations, backups, health checks, rollback, security and troubleshooting.