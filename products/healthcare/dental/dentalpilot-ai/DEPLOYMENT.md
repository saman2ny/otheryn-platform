# Deployment (Docker Compose / VPS)

> **Consolidated.** The authoritative deployment guide is [`docs/notion/SETUP_AND_DEPLOYMENT.md`](docs/notion/SETUP_AND_DEPLOYMENT.md).

## Compose/VPS quick start

```bash
cp .env.production.example .env.production
# Place SSL certs in nginx/ssl/: fullchain.pem, privkey.pem, chain.pem
./deploy.sh production
```

Operational files remain at the repository root:

- `docker-compose.yml` — production stack (GHCR images)
- `docker-compose.staging.yml` — staging overrides (HTTP-only, port 8080)
- `deploy.sh` — production/staging helper
- `nginx/conf.d/default.conf`, `nginx/staging/default.conf`
- `.env.production.example`, `.env.staging.example`

See [`docs/notion/SETUP_AND_DEPLOYMENT.md`](docs/notion/SETUP_AND_DEPLOYMENT.md) for the full procedure, backups, rollback and security.