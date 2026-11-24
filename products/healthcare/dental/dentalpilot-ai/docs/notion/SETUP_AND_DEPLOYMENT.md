# DentalPilot AI — Setup & Deployment

**Audience:** developers, DevOps/platform engineers.
**Scope:** local development (Docker-first) and production deployment. For business context see [`BUSINESS_PROPOSAL.md`](BUSINESS_PROPOSAL.md); for engineering design see [`TECHNICAL_ARCHITECTURE.md`](TECHNICAL_ARCHITECTURE.md); for version history see [`RELEASE_NOTES.md`](../../RELEASE_NOTES.md).

> This document is the single operational guide. It consolidates the former `LOCAL_DEVELOPMENT.md`, `ENVIRONMENT_GUIDE.md`, `RAILWAY_DEPLOYMENT.md` and `DEPLOYMENT.md`.

---

## A. System prerequisites

| Tool | Version | Used for |
|---|---|---|
| Docker | 24+ | Containers, Compose |
| Docker Compose | v2 (`docker compose`) | Local and production stacks |
| Node.js | 22 LTS recommended (20.19+ / 22.12+ / 24.x) | Angular frontend |
| npm | 11 (`packageManager` `11.6.2`) | Frontend dependencies |
| Python | **3.12** recommended | Backend (3.14 may lack wheels) |
| PostgreSQL | 16 | Production/local Docker; SQLite is the native default |
| Redis | 7 | Provisioned in Compose but **not used by app code** |
| Git | any recent | Source control |

Verify:

```bash
docker --version
docker compose version
node --version
npm --version
python3.12 --version
```

**Ports:** `4200` Angular, `8000` FastAPI, `5432` Postgres, `6379` Redis.

### A.1 Version verification (tested vs deployed)

| Component | Tested locally | Deployment configuration | Recommended |
|---|---|---|---|
| Node.js | v24.16.0 | `frontend/Dockerfile`: `node:20-alpine` (floating) | Node 22 LTS |
| npm | 11.20.0 | `packageManager` `npm@11.6.2` | 11.x |
| Angular | 21.2.18 (lockfile) | `npm ci` from `package-lock.json` | 21.2.x |
| TypeScript | 5.9.3 (lockfile) | same | 5.9.x |
| Vitest | 4.1.10 (lockfile) | same | 4.x |
| Python | 3.12 (Docker `python:3.12-slim`) | Railway Nixpacks `python311` (3.11) | 3.12 (align Railway) |
| FastAPI | 0.139.2 | same | 0.139.x |
| SQLAlchemy | 2.0.51 | same | 2.0.x |
| Alembic | 1.18.5 | same | 1.18.x |

Angular 21 requires Node `^20.19.0 || ^22.12.0 || ^24.0.0`. `node:20-alpine` is a floating tag; pin a specific 20.19+ tag or digest for reproducible builds.

**Known mismatch:** Railway uses Python 3.11 (Nixpacks) while the Dockerfile and local tests use Python 3.12. Align before standardizing. Do not change configuration as part of documentation.

---

## B. Local development architecture

The repository provides `docker-compose.local.yml` (Docker-first) for **PostgreSQL, Redis, a one-shot migration, the FastAPI backend and the workers**. The **Angular frontend is not in Compose** — run it natively (`ng serve`) for the fastest HMR, or in a Node container (see §C).

| Service | Image/build | Port | Volume | Depends on |
|---|---|---|---|---|
| `postgres` | `postgres:16-alpine` | `5432` | `postgres_local_data` | — |
| `redis` | `redis:7-alpine` | `6379` | `redis_local_data` | — (unused by app) |
| `migrate` | build `./backend` | — | — | `postgres` healthy |
| `backend` | build `./backend` | `8000` | bind mounts `./backend/app`, `./backend/alembic`, `./backend/alembic.ini`, `./backend/scripts` | `postgres`, `redis`, `migrate` completed |
| `workers` | build `./backend` | — | bind mount `./backend/app` | `postgres`, `redis`, `migrate` completed |

Network: `dentalpilot-local` (bridge). The backend command is `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`; the workers command is `python -m app.workers.run_workers`.

**Redis:** the application does not use Redis. No Redis client is installed or imported; the outbox workers are PostgreSQL-backed. The Redis container is optional and can be ignored/removed from the local stack.

---

## C. Local frontend setup

### C.1 Native (recommended, fastest HMR)

```bash
cd products/healthcare/dental/dentalpilot-ai/frontend
npm ci
npm start          # ng serve → http://localhost:4200
```

- Environment: `src/environments/environment.ts` → `apiBaseUrl: 'http://localhost:8000/api/v1'`.
- Production build: `npm run build` → `dist/dentalpilot-ai/browser/`.
- Unit tests: `npm test` (Vitest; add `--watch=false` for a single run).
- Formatting: `npx prettier --check "src/**/*.{ts,html,css}"` (there is no `lint` script).

### C.2 Docker (optional, hot reload)

The production `frontend/Dockerfile` is a build image, not a dev server. For a containerized dev server with hot reload, run a Node container with bind mounts:

```bash
cd products/healthcare/dental/dentalpilot-ai
docker run --rm -it \
  -p 4200:4200 \
  -v "$PWD/frontend:/app" \
  -v dentalpilot-frontend-node-modules:/app/node_modules \
  -w /app \
  node:22 \
  sh -c "npm ci && npm start -- --host 0.0.0.0 --port 4200 --poll 1000"
```

- The named volume caches `node_modules` across runs.
- `--poll 1000` is important for **reliable file watching on macOS** with Docker bind mounts.
- Open <http://localhost:4200>.

### C.3 Hot reload behaviour

`ng serve` uses the `@angular/build:dev-server` builder with the `development` configuration. Verified startup output:

```text
Watch mode enabled. Watching for file changes...
  ➜  Local:   http://localhost:4200/
```

| Change | Result |
|---|---|
| `.ts` component/service | Rebuild; browser updates |
| `.html` template | Rebuild; view updates |
| `.css` / `.scss` | Styles rebuilt and re-applied |
| `angular.json` / `package.json` | Dev server may restart |

No manual restart is required for ordinary edits. Production builds do not watch.

### C.4 Frontend troubleshooting

| Problem | Fix |
|---|---|
| `npm ci` fails | Use Node 20.19+/22.12+/24 and npm 11 |
| Changes not detected in Docker | Add `--poll 1000`; ensure bind mount |
| Port 4200 in use | `lsof -i :4200` |
| App loads but API fails | Start the backend on `:8000`; check `CORS_ORIGINS` |
| Build fails after pull | `rm -rf node_modules dist .angular && npm ci` |

---

## D. Local backend setup

### D.1 Native (SQLite or local Postgres)

```bash
cd products/healthcare/dental/dentalpilot-ai/backend
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: JWT_SECRET, DATABASE_URL, CORS_ORIGINS

alembic upgrade head
python scripts/seed_hierarchy.py
uvicorn app.main:app --reload --reload-dir app --port 8000
```

- Swagger UI: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>, `/health/live`, `/health/ready`
- API base: `http://localhost:8000/api/v1`
- Tests: `pytest tests/ -q`

### D.2 Docker (Compose)

The `backend` service in `docker-compose.local.yml` builds from `backend/Dockerfile`, mounts the source, and runs with `--reload`. Migrations are handled by the one-shot `migrate` service — **do not run `alembic upgrade head` again manually** in this mode.

```bash
docker compose -f docker-compose.local.yml logs -f backend
```

### D.3 Hot reload behaviour

`uvicorn --reload` watches Python files and restarts the server. Verified options: `--reload-dir`, `--reload-include`, `--reload-exclude`.

| Change | Restarts? |
|---|---|
| Python file under `app/` | **Yes** |
| `.env` / environment variables | **No** — restart manually |
| `requirements.txt` / new dependency | **No** — install, restart |
| Alembic migration | **No** — run `alembic upgrade head`, then restart |

Recommended: `uvicorn app.main:app --reload --reload-dir app --port 8000`.

**macOS note:** if file events do not propagate through Docker Desktop bind mounts, run the backend natively (D.1) or use a polling-based watcher. Production must never use `--reload`.

### D.4 Backend troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Activate venv; use Python 3.12 |
| `psycopg2` error | `DATABASE_URL` must use `postgresql+psycopg://` |
| `alembic upgrade head` fails on SQLite | Use Docker/PostgreSQL (known revision `e78cbd0fad9c` issue) |
| `JWT_SECRET` error | Set a 32+ char non-default secret in production |
| `503` on AI/payments/storage | Integration not configured — expected |
| `alembic` cannot find config | Run from `backend/` |

---

## E. Local background worker

### E.1 Purpose

The worker runs three database-backed loops: `email_outbox`, `communication_outbox`, `subscription_billing`. It does not serve HTTP and does not run migrations.

### E.2 Native

```bash
cd products/healthcare/dental/dentalpilot-ai/backend
source .venv/bin/activate
python -m app.workers.run_workers
```

Verified startup output:

```text
INFO:app.workers.email_outbox:Starting DentalPilot email outbox worker.
INFO:app.workers.communication_outbox:Starting DentalPilot communication outbox worker.
INFO:app.workers.subscription_billing:Starting the subscription billing webhook worker.
```

### E.3 Docker

The `workers` service in `docker-compose.local.yml` runs `python -m app.workers.run_workers` with the same image and bind mount as the backend.

### E.4 Logs, shutdown, restart

- Logs: `docker compose -f docker-compose.local.yml logs -f workers` or the native process stdout.
- Stop: `Ctrl+C` (SIGINT).
- Restart: run the command again.
- **Do not run two workers against the same database** — they compete for outbox rows.

### E.5 Development auto-reload (optional)

The worker has no built-in reload. Use `watchfiles` (already a dependency, v1.2.0):

```bash
watchfiles --filter python --sigint-timeout 5 "python -m app.workers.run_workers" app
```

Stop the Compose `workers` service first to avoid duplicates.

### E.6 Known limitation

If the database is unreachable or the schema is missing, each worker thread logs an exception and exits; the process does not restart dead threads. In production, Railway's `ON_FAILURE` restart policy restarts the process if it exits, but a single dead thread is not revived while others run. This is a robustness gap, not a configuration error.

---

## F. Local database

### F.1 PostgreSQL (Docker)

`docker-compose.local.yml` starts `postgres:16-alpine`:

- Container: `dentalpilot-local-postgres`
- Port: `5432`
- Database: `dentalpilot` (`POSTGRES_DB`)
- User: `dentalpilot` (`POSTGRES_USER`)
- Password: `POSTGRES_PASSWORD` from `.env.local`
- Volume: `postgres_local_data`
- Health check: `pg_isready`

Connection strings:

```dotenv
# Inside Compose
DATABASE_URL=postgresql+psycopg://dentalpilot:<POSTGRES_PASSWORD>@postgres:5432/dentalpilot
# From the host
DATABASE_URL=postgresql+psycopg://dentalpilot:<POSTGRES_PASSWORD>@localhost:5432/dentalpilot
```

Verify:

```bash
docker compose -f docker-compose.local.yml exec postgres pg_isready -U dentalpilot -d dentalpilot
```

### F.2 SQLite (native)

- Default `DATABASE_URL=sqlite:///./dentalpilot.db`.
- File is created in `backend/`.
- Migrations: `alembic upgrade head`.
- **Known issue:** the SQLite migration chain fails at `e78cbd0fad9c` (`ValueError: Constraint must have a name`). Use PostgreSQL for a reliable local setup.

### F.3 Redis

- `docker-compose.local.yml` starts `redis:7-alpine` on `6379`.
- **The application does not use Redis.** No Redis client is installed or imported; the workers are PostgreSQL-backed.
- Treat Redis as optional and unused.

### F.4 Migrations and seeding

```bash
alembic upgrade head
alembic current
alembic history
python scripts/seed_hierarchy.py
```

`python scripts/seed_hierarchy.py` creates local demo accounts (super admin, owner, staff) and prints their credentials to stdout. Run it **only against a local database**; never against staging or production, and never commit or publish the printed credentials.

### F.5 Backup and restore (local)

```bash
# Backup
docker compose -f docker-compose.local.yml exec -T postgres pg_dump -U dentalpilot dentalpilot > backup.sql

# Restore (destructive)
docker compose -f docker-compose.local.yml exec -T postgres psql -U dentalpilot dentalpilot < backup.sql
```

---

## G. One-command local startup

Docker Compose starts PostgreSQL, Redis, the one-shot migration, the FastAPI backend and the workers. The frontend runs separately.

```bash
cd products/healthcare/dental/dentalpilot-ai
cp .env.local.example .env.local
# Edit .env.local: POSTGRES_PASSWORD, JWT_SECRET, DATABASE_URL (host `postgres`)

docker compose -f docker-compose.local.yml up -d --build
docker compose -f docker-compose.local.yml ps
```

Frontend (second terminal):

```bash
cd products/healthcare/dental/dentalpilot-ai/frontend
npm ci
npm start
```

Open **<http://localhost:4200>**.

### G.1 Common commands

```bash
# Status
docker compose -f docker-compose.local.yml ps

# Logs
docker compose -f docker-compose.local.yml logs -f backend workers

# Stop (keeps volumes)
docker compose -f docker-compose.local.yml stop

# Stop and remove containers (keeps volumes)
docker compose -f docker-compose.local.yml down

# Restart
docker compose -f docker-compose.local.yml restart backend workers

# Rebuild
docker compose -f docker-compose.local.yml up -d --build

# Database access
docker compose -f docker-compose.local.yml exec postgres psql -U dentalpilot dentalpilot

# Reset local data (DESTRUCTIVE — local volumes only)
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up -d --build
```

### G.2 Local URLs

| Service | URL / port |
|---|---|
| Angular dev server | <http://localhost:4200> |
| FastAPI | <http://localhost:8000> |
| Swagger UI | <http://localhost:8000/docs> |
| Health | <http://localhost:8000/health> |
| Readiness | <http://localhost:8000/health/ready> |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` (unused) |

---

## H. Production deployment

Production runs on **Railway** with four managed services: **frontend**, **backend**, **worker** and **PostgreSQL**. Redis is not used. A Docker Compose/VPS alternative is also supported (see §H.5).

### H.1 Frontend

1. Railway → **New Project → Deploy from GitHub repo** (`saman2ny/otheryn-platform`).
2. Add a service → **Root Directory** = `products/healthcare/dental/dentalpilot-ai/frontend` (or `frontend`).
3. Railway detects `frontend/Dockerfile` (`node:20-alpine` builder → `npm ci && npm run build` → `nginx:alpine`).
4. **Build-time API URL:** `src/environments/environment.prod.ts` → `https://api.dentalpilot.in/api/v1`. Changing Railway variables does **not** change the Angular bundle; edit the file and rebuild.
5. **Settings → Networking → Generate Domain**; add CNAMEs for `dentalpilot.in` and `www.dentalpilot.in`; TLS is automatic.
6. Nginx (`frontend/nginx.conf`) serves the SPA, proxies `/api/` to `https://api.dentalpilot.in`, returns `/health` = `healthy`, and caches hashed assets for 1 year.
7. Verify: `curl -I https://dentalpilot.in/health`, `curl -s https://dentalpilot.in/ | head -5`.
8. Rollback: Railway → Deployments → previous → Redeploy.

### H.2 Backend API

1. Add a service → **Root Directory** = `products/healthcare/dental/dentalpilot-ai/backend` (or `backend`).
2. Builder: **Nixpacks** (`railway.toml`). Railway reads `railway.toml` and `nixpacks.toml` from the service root.
3. Start command (from `railway.toml`, do **not** override):
   ```bash
   alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Python runtime: `nixpacks.toml` selects `python311`; the Dockerfile uses Python 3.12 (mismatch — see §K).
5. Required variables: `DATABASE_URL` (`postgresql+psycopg://`), `JWT_SECRET`, `APP_ENVIRONMENT=production`, `CORS_ORIGINS`.
6. Health check path: `/health`.
7. Generate domain `api.dentalpilot.in`; TLS automatic.
8. Verify: `curl https://api.dentalpilot.in/health`, `/health/ready`.
9. Logs: Railway → Deployments → Build/Deploy/HTTP Logs, or `railway logs`.

### H.3 Background worker

1. Add a **separate Railway service** from the same repo.
2. **Root Directory** = backend root.
3. **Custom Start Command**: `python -m app.workers.run_workers`.
4. Same `DATABASE_URL`, `JWT_SECRET`, `APP_ENVIRONMENT` and integration variables as the backend.
5. No public domain, no health path.
6. The worker **must not run migrations** — the backend start command runs `alembic upgrade head`; the worker only polls.
7. Logs: Railway → Deployments → Deploy Logs; restart via Redeploy.

### H.4 Database

1. Railway → **New → Database → PostgreSQL**.
2. Set `DATABASE_URL` on backend and worker:
   ```dotenv
   DATABASE_URL=postgresql+psycopg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
   ```
   **Critical:** use `postgresql+psycopg://`; Railway's `${{Postgres.DATABASE_URL}}` is `postgresql://` and SQLAlchemy would try `psycopg2` (not installed).
3. Use Railway private networking; do not expose Postgres publicly.
4. Migrations: the backend start command runs `alembic upgrade head` on every deploy. Do not add a separate migration service.
5. Inspect: `railway run alembic current`, `railway run alembic history`.
6. Backup: enable Railway backups/PITR; logical backup:
   ```bash
   railway run pg_dump "$DATABASE_URL" > dentalpilot-$(date +%F).sql
   ```
   Restore (destructive):
   ```bash
   railway run psql "$DATABASE_URL" < dentalpilot-YYYY-MM-DD.sql
   ```

### H.5 Docker Compose / VPS (alternative)

The repository also supports a Compose-based production stack (`docker-compose.yml` + `deploy.sh`):

```bash
cp .env.production.example .env.production
# Place SSL certs in nginx/ssl/: fullchain.pem, privkey.pem, chain.pem
./deploy.sh production
```

- Images are pulled from GHCR (`REGISTRY/IMAGE_NAME-backend|frontend:IMAGE_TAG`).
- The one-shot `migrate` service runs `alembic upgrade head` before backend/workers.
- `docker-compose.staging.yml` overrides to HTTP-only on `8080` with `nginx/staging/default.conf`.
- `deploy.sh` validates `.env.${ENVIRONMENT}`, pulls images, runs `up -d`, and health-checks.

---

## I. Environment variables

| Variable | Service | Required | Purpose | Local / Production | Setting |
|---|---|---|---|---|---|
| `APP_ENVIRONMENT` | backend, worker | ✅ | Environment mode | both | runtime |
| `DATABASE_URL` | backend, worker | ✅ | SQLAlchemy URL (`postgresql+psycopg://`) | both | runtime |
| `JWT_SECRET` | backend, worker | ✅ | JWT signing (32+ chars prod) | both | runtime |
| `JWT_ALGORITHM` | backend, worker | optional | JWT algorithm | both | runtime |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | backend | optional | Access token lifetime | both | runtime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | backend | optional | Refresh token lifetime | both | runtime |
| `CORS_ORIGINS` | backend | ✅ prod | Allowed origins (JSON array) | both | runtime |
| `XAI_API_KEY` | backend, worker | optional | xAI Grok API key | both | runtime |
| `XAI_MODEL` | backend, worker | optional | Grok model | both | runtime |
| `XAI_BASE_URL` | backend, worker | optional | xAI API base URL | both | runtime |
| `CLINICAL_NOTE_DRAFTING_ENABLED` | backend | optional | AI note drafting | both | runtime |
| `CLINICAL_AI_DATA_PROCESSING_APPROVED` | backend | optional | Consent gate | both | runtime |
| `RAZORPAY_KEY_ID` | backend, worker | optional | Razorpay key | both | runtime |
| `RAZORPAY_KEY_SECRET` | backend, worker | optional | Razorpay secret | both | runtime |
| `RAZORPAY_WEBHOOK_SECRET` | backend, worker | required with Razorpay | Webhook verification | both | runtime |
| `RAZORPAY_CURRENCY` | backend, worker | optional | Subscription currency | both | runtime |
| `RAZORPAY_PLAN_IDS` | backend, worker | required with Razorpay | Plan IDs (JSON) | both | runtime |
| `PATIENT_PAYMENT_CURRENCY` | backend, worker | optional | Treatment payment currency | both | runtime |
| `S3_BUCKET` | backend, worker | optional | Document bucket | both | runtime |
| `S3_ENDPOINT_URL` | backend, worker | optional | S3-compatible endpoint | both | runtime |
| `AWS_REGION` | backend, worker | optional | AWS region | both | runtime |
| `S3_KMS_KEY_ID` | backend, worker | optional | KMS key | both | runtime |
| `MAX_PATIENT_DOCUMENT_BYTES` | backend, worker | optional | Upload limit | both | runtime |
| `SMTP_HOST` | backend, worker | optional | SMTP server | both | runtime |
| `SMTP_PORT` | backend, worker | optional | SMTP port | both | runtime |
| `SMTP_USERNAME` | backend, worker | optional | SMTP user | both | runtime |
| `SMTP_PASSWORD` | backend, worker | optional | SMTP password | both | runtime |
| `SMTP_SENDER_EMAIL` | backend, worker | optional | Sender | both | runtime |
| `SMTP_SENDER_NAME` | backend, worker | optional | Sender name | both | runtime |
| `SMTP_USE_SSL` | backend, worker | optional | Implicit SSL | both | runtime |
| `SMTP_USE_STARTTLS` | backend, worker | optional | STARTTLS | both | runtime |
| `EMAIL_WORKER_INTERVAL_SECONDS` | worker | optional | Email poll | both | runtime |
| `EMAIL_MAX_ATTEMPTS` | worker | optional | Email retries | both | runtime |
| `WHATSAPP_PHONE_NUMBER_ID` | backend, worker | optional | WhatsApp sender | both | runtime |
| `WHATSAPP_ACCESS_TOKEN` | backend, worker | optional | WhatsApp token | both | runtime |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | backend, worker | optional | Webhook verification | both | runtime |
| `SUBSCRIPTION_GRACE_PERIOD_DAYS` | worker | optional | Grace period | both | runtime |
| `BILLING_WEBHOOK_INTERVAL_SECONDS` | worker | optional | Billing poll | both | runtime |
| `BILLING_WEBHOOK_MAX_ATTEMPTS` | worker | optional | Billing retries | both | runtime |
| `SUBSCRIPTION_RECONCILIATION_INTERVAL_SECONDS` | worker | optional | Reconciliation | both | runtime |
| `POSTGRES_USER` | Compose Postgres | local/prod Compose | DB user | Compose | runtime |
| `POSTGRES_PASSWORD` | Compose Postgres | local/prod Compose | DB password | Compose | runtime |
| `POSTGRES_DB` | Compose Postgres | local/prod Compose | DB name | Compose | runtime |
| `POSTGRES_PORT` | local Compose | local | Host port | local | runtime |
| `REDIS_PORT` | local Compose | local | Redis port (unused) | local | runtime |
| `BACKEND_PORT` | local Compose | local | Backend port | local | runtime |
| `REGISTRY` / `IMAGE_NAME` / `IMAGE_TAG` | production Compose | prod | Image refs | production | runtime |

**Frontend:** no runtime variables. `apiBaseUrl` is set in `src/environments/environment.prod.ts` at **build time**.

**Secrets:** never commit `.env`, `.env.local`, `.env.production`, `.env.staging`. Use Railway variables or a secret manager.

---

## J. Production vs local separation

| Concern | Local | Production |
|---|---|---|
| Frontend | `ng serve` (or Node container) | Nginx + static Angular build |
| Backend | `uvicorn --reload` | `uvicorn` **without** `--reload` |
| Workers | `python -m app.workers.run_workers` (native or Compose) | Same command, separate Railway service; no dev watcher |
| Database | Local Postgres/SQLite | Railway Postgres |
| Config | `.env.local` / `backend/.env` | Railway variables |
| Secrets | Local-only values | Railway/secret manager |
| Data | Local volumes/files | Railway-managed, separate |

**Rules:**
- Development hot reload is local only.
- Production frontend uses the production web server.
- Production backend does not use Uvicorn `--reload`.
- Production workers do not use development watchers.
- Production credentials are never committed.
- Local and production environment configurations are separate.
- **Never point a local `.env` at a production database.**

---

## K. Troubleshooting (including historical incidents)

| Symptom | Fix |
|---|---|
| `npm ci` fails | Node 20.19+/22.12+/24, npm 11 |
| Frontend changes not detected (Docker) | `--poll 1000` |
| `alembic upgrade head` fails on SQLite | Use Docker/PostgreSQL (revision `e78cbd0fad9c`) |
| `psycopg2` error | `DATABASE_URL` must be `postgresql+psycopg://` |
| `JWT_SECRET` error in production | 32+ chars, non-default |
| Worker logs `no such table` | Migrations not applied |
| Worker thread dies | Check DB connectivity; restart the worker |
| Port already in use | `lsof -i :8000` / `:4200` / `:5432` |
| Railway build fails | Root directory must contain `railway.toml` / `Dockerfile`; do not set a Custom Start Command for the backend |
| Railway build: `No module named pip` | Do not override `[phases.install]` in `nixpacks.toml` (historical incident) |
| Railway serves an old commit | Check the deployment **Details** SHA before re-debugging; reconnect GitHub or redeploy |
| Production 502 from frontend | Backend not running; check `/api/` proxy target |
| Production `psycopg2` error | `DATABASE_URL` scheme |
| CORS headers missing on 500 | `CatchAllExceptionMiddleware` must be registered **before** `CORSMiddleware` (historical bug) |
| Deployed commit is old | Railway → Deployments → Details → SHA |

**Security action — demo accounts:** the local seed script creates known demo accounts. If it was ever run against a deployed database (historical documentation claims it was), those accounts must be **rotated or removed immediately** and their credentials must not be reused. Verify with the production owner; do not assume they are active or inactive.

---

## L. Verification status

| Claim | Status |
|---|---|
| Local Compose configuration | Configuration validated (`docker compose config`) |
| Local backend container + tests | Locally tested (25 passed, 0 failed) |
| Local frontend build + tests | Locally tested (build + 1 test) |
| Angular dev server watch mode | Locally tested (starts in watch mode; no live edit test) |
| Uvicorn `--reload` | Configuration validated (options); not live-tested |
| Worker startup | Locally tested (3 threads start; DB error path observed) |
| Nginx configurations | Configuration validated (`nginx -t`) |
| Railway production deployment | Documented — **not executed** |
| Production verify/rollback | Documented — **not executed** |
| Backup/restore | Documented — **not executed** |
| Production behavior/security | **Not verified** |

No production deployment, backup/restore, or production behavior was executed during this documentation effort.

---

## M. Related documentation

- [`BUSINESS_PROPOSAL.md`](BUSINESS_PROPOSAL.md) — business strategy.
- [`TECHNICAL_ARCHITECTURE.md`](TECHNICAL_ARCHITECTURE.md) — engineering design.
- [`RELEASE_NOTES.md`](../../RELEASE_NOTES.md) — version history.
- [`../../AUDIT/PRODUCT_IMPLEMENTATION_AUDIT.md`](../../AUDIT/PRODUCT_IMPLEMENTATION_AUDIT.md) — evidence-based audit.
- [`../../frontend/README.md`](../../frontend/README.md) — frontend component guide.
- [`../../backend/README.md`](../../backend/README.md) — backend component guide.