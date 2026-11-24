# Local Development

> **Consolidated.** The authoritative local development guide is [`docs/notion/SETUP_AND_DEPLOYMENT.md`](docs/notion/SETUP_AND_DEPLOYMENT.md).

It covers Docker Compose (PostgreSQL, Redis, backend, workers), the Angular dev server, hot reload, migrations, seeding, shutdown/logs and troubleshooting.

## Quick start

```bash
cd products/healthcare/dental/dentalpilot-ai
cp .env.local.example .env.local
# Edit .env.local: POSTGRES_PASSWORD, JWT_SECRET, DATABASE_URL (host `postgres`)

docker compose -f docker-compose.local.yml up -d --build

cd frontend
npm ci
npm start          # http://localhost:4200
```

- API: <http://localhost:8000> · Swagger: <http://localhost:8000/docs>
- Frontend: <http://localhost:4200>
- Stop: `docker compose -f docker-compose.local.yml stop`

See [`docs/notion/SETUP_AND_DEPLOYMENT.md`](docs/notion/SETUP_AND_DEPLOYMENT.md) for the complete guide.