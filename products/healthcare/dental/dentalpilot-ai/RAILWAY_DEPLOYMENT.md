# Railway Deployment

> **Consolidated.** The authoritative production deployment guide is [`docs/notion/SETUP_AND_DEPLOYMENT.md`](docs/notion/SETUP_AND_DEPLOYMENT.md).

It covers Railway frontend, backend, worker and PostgreSQL services, domains, TLS, migrations, backups, rollbacks and troubleshooting.

## Railway services (summary)

| Service | Root | Build | Start |
|---|---|---|---|
| Backend | `products/healthcare/dental/dentalpilot-ai/backend` | Nixpacks (`railway.toml`) | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Worker | same | same | `python -m app.workers.run_workers` |
| Frontend | `products/healthcare/dental/dentalpilot-ai/frontend` | Dockerfile (`node:20-alpine` → `nginx:alpine`) | Nginx |
| PostgreSQL | Railway-managed | — | — |

**Critical:** `DATABASE_URL` must use `postgresql+psycopg://`. **No Uvicorn `--reload` in production.**

See [`docs/notion/SETUP_AND_DEPLOYMENT.md`](docs/notion/SETUP_AND_DEPLOYMENT.md) for the full procedure.