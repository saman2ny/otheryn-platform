# DentalPilot AI — Local Development

Complete local setup for the Angular frontend, FastAPI backend, background workers and database, including verified hot-reload behaviour.

> Read [`README.md`](README.md) first for the product overview and production deployment. This document is local development only.

---

## 1. Overview

| Component | Local technology | Port | Started by |
|---|---|---|---|
| Frontend | Angular 21 dev server (`ng serve`) | `4200` | You, in a terminal |
| Backend | FastAPI + Uvicorn (`--reload`) | `8000` | Docker Compose **or** your terminal |
| Workers | `python -m app.workers.run_workers` | — | Docker Compose **or** your terminal |
| PostgreSQL | PostgreSQL 16 (Docker) | `5432` | Docker Compose **or** Docker |
| Redis | Redis 7 (Docker) | `6379` | Docker Compose — **not used by app code** |

Two supported workflows:

1. **Docker + PostgreSQL** (recommended): Compose starts Postgres, Redis, migrations, the backend and the workers. You run only the Angular dev server.
2. **Native**: you run the backend, workers and frontend yourself, with SQLite or a local Postgres.

Do not run both workflows at the same time — you would start duplicate backend/worker processes against the same database.

---

## 2. Prerequisites

- **Docker** 24+ with **Docker Compose v2** (`docker compose`, not `docker-compose`).
- **Node.js** 22 LTS recommended (20.19+ minimum) and **npm 11**.
- **Python 3.12** (Python 3.14 may lack wheels for the pinned dependencies).
- **Git**.
- Free ports: `4200`, `8000`, `5432`, `6379`.

Verify:

```bash
docker --version
docker compose version
node --version
npm --version
python3.12 --version
```

---

## 3. Local frontend setup

### 3.1 Directory

```bash
cd products/healthcare/dental/dentalpilot-ai/frontend
```

> **The frontend is not containerized locally.** `docker-compose.local.yml` intentionally excludes it — use `ng serve` for fast HMR. For the production Docker image, see [`frontend/README.md`](frontend/README.md).

### 3.2 Install dependencies

```bash
npm ci
```

`npm ci` installs exactly what `package-lock.json` specifies. Use `npm install` only when you intentionally change dependencies.

### 3.3 Environment configuration

`src/environments/environment.ts` is used by `ng serve`:

```ts
export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8000/api/v1',
};
```

No change is needed for local development. To use a different backend URL, edit this file.

### 3.4 Start the dev server

```bash
npm start          # ng serve
```

Open **<http://localhost:4200>**.

### 3.5 Backend API URL

The frontend calls `http://localhost:8000/api/v1`. Ensure the backend is running and `CORS_ORIGINS` includes `http://localhost:4200`.

### 3.6 Production build

```bash
npm run build
```

Output: **`dist/dentalpilot-ai/browser/`**.

### 3.7 Unit tests

```bash
npm test           # ng test (Vitest)
```

`ng test` runs in watch mode in a TTY and once otherwise. To force a single run:

```bash
npx ng test --watch=false
```

### 3.8 Troubleshooting

| Problem | Fix |
|---|---|
| `npm ci` fails | Use Node 20.19+/22.12+/24 and npm 11 |
| `ng: command not found` | Run `npm ci` first |
| App loads but API calls fail | Start the backend on `:8000`; check `CORS_ORIGINS` |
| Port 4200 in use | `lsof -i :4200` |
| Build fails after a pull | `rm -rf node_modules dist .angular && npm ci` |

---

## 4. Frontend hot reload

**Verified:** `npm start` starts the Angular dev server and prints:

```text
Application bundle generation complete.
Watch mode enabled. Watching for file changes...
  ➜  Local:   http://localhost:4200/
```

This confirms the dev server is in watch mode. The behaviour on save:

| File type | What happens | Browser |
|---|---|---|
| TypeScript (`.ts`) | Rebuild; the page reloads / components refresh | Updates automatically |
| HTML template (`.html`) | Rebuild; the view updates | Updates automatically |
| CSS/SCSS (`.css`, `.scss`) | Styles rebuild; styles are re-applied | Updates without a full reload where possible |
| `angular.json` / `package.json` | Dev server may restart | May require a manual refresh |

- **No manual restart is required** for ordinary source edits.
- The dev server uses the `@angular/build:dev-server` builder with the `development` configuration (from `angular.json`).
- Production builds (`npm run build`) do **not** watch or hot reload.

### File-watching problems

If changes are not detected (common on network shares, Docker-mounted volumes, or some editors):

```bash
# Poll for changes every 1000 ms
npm start -- --poll 1000
```

Also ensure your editor saves files (not atomic-save to a temp file that the watcher misses) and that the project is not on a synced/virtual filesystem.

> I verified that the dev server starts in watch mode. I did not perform a live file-edit reload during this audit because no source files were modified.

---

## 5. Local backend setup

### 5.1 Directory

```bash
cd products/healthcare/dental/dentalpilot-ai/backend
```

### 5.2 Python and virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

### 5.3 Install dependencies

```bash
pip install -r requirements.txt
```

### 5.4 Environment file

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```dotenv
JWT_SECRET=<output of: openssl rand -base64 48>
DATABASE_URL=sqlite:///./dentalpilot.db
APP_ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:4200"]
```

### 5.5 Database configuration

- **SQLite (default):** `DATABASE_URL=sqlite:///./dentalpilot.db`.
- **PostgreSQL:** `DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:5432/<db>` (the `+psycopg` driver is required).

### 5.6 Migrations

```bash
alembic upgrade head
alembic current
alembic history
```

> **Known SQLite issue:** `alembic upgrade head` on SQLite may fail at revision `e78cbd0fad9c` with `ValueError: Constraint must have a name`. Use the Docker/PostgreSQL workflow (§9) or apply the named-constraint fix.

### 5.7 Seed data

```bash
python scripts/seed_hierarchy.py
```

Creates one demo clinic and three users (password `password123`):

| Role | Email |
|---|---|
| Super Admin | `super-admin@dentalpilot.ai` |
| Clinic Owner | `owner@brightsmiledental.io` |
| Clinic Staff | `staff@brightsmiledental.io` |

Local only — never use these credentials in staging or production.

### 5.8 Start FastAPI

```bash
uvicorn app.main:app --reload --reload-dir app --port 8000
```

- **Swagger UI:** <http://localhost:8000/docs>
- **Health:** <http://localhost:8000/health>
- **Readiness:** <http://localhost:8000/health/ready>
- **API base:** `http://localhost:8000/api/v1`

### 5.9 Backend tests

```bash
pytest tests/ -q
```

### 5.10 Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Activate the venv; use Python 3.12 |
| `psycopg2` error | `DATABASE_URL` must use `postgresql+psycopg://` |
| `JWT_SECRET` error | Set a 32+ char non-default secret in production |
| `503` on AI/payments/storage | The integration is not configured — expected |
| `alembic` cannot find config | Run from `backend/` |

### 5.11 Docker-based backend (Compose)

The recommended local backend runs in Docker via `docker-compose.local.yml`. The `backend` service builds from `backend/Dockerfile`, mounts the source (`./backend/app`, `./backend/alembic`, `./backend/scripts`), and starts with hot reload:

```yaml
command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

Because the source is mounted, Python edits under `app/` trigger a reload inside the container. Migrations are handled by the one-shot `migrate` service — do not run `alembic upgrade head` again manually.

```bash
docker compose -f docker-compose.local.yml logs -f backend
```

---

## 6. Backend hot reload

**Verified:** `uvicorn --reload` is available and supports `--reload-dir`, `--reload-include` and `--reload-exclude`.

| Change | Restarts the server? |
|---|---|
| Python file under `app/` (`.py`) | **Yes** — Uvicorn restarts |
| `alembic/` migration file | Yes if under a watched directory; not needed at runtime |
| `.env` / environment variables | **No** — restart manually |
| `requirements.txt` / new dependency | **No** — stop, install, restart |
| `alembic.ini` | **No** — restart manually |
| Database schema change | **No** — run `alembic upgrade head`, then restart |

Recommended local command:

```bash
uvicorn app.main:app --reload --reload-dir app --port 8000
```

- `--reload-dir app` limits watching to the application source (faster, avoids restarting on unrelated files).
- Default watch includes `*.py`; default excludes `.*, .py[cod], .sw.*, ~*`.
- Add `--reload-include`/`--reload-exclude` if you need different patterns.

**Production must never use `--reload`.** Production runs `uvicorn` without reload (see `railway.toml` / Docker Compose).

---

## 7. Local background worker

### 7.1 Purpose

The worker process runs three database-backed loops:

1. `email_outbox` — sends queued patient emails via SMTP.
2. `communication_outbox` — sends queued patient email/SMS/WhatsApp messages.
3. `subscription_billing` — processes Razorpay webhook events, renewals, failures, grace periods and cancellations.

It does **not** run migrations and does **not** serve HTTP.

### 7.2 Dependencies and environment

- Same virtual environment and `.env` as the backend.
- Requires a **migrated database**.
- Uses the same `DATABASE_URL`, `SMTP_*`, `WHATSAPP_*`, `RAZORPAY_*` variables as the backend.

### 7.3 Start directory and command

```bash
cd products/healthcare/dental/dentalpilot-ai/backend
source .venv/bin/activate
python -m app.workers.run_workers
```

Startup output (verified):

```text
INFO:app.workers.email_outbox:Starting DentalPilot email outbox worker.
INFO:app.workers.communication_outbox:Starting DentalPilot communication outbox worker.
INFO:app.workers.subscription_billing:Starting the subscription billing webhook worker.
```

### 7.4 Logging

The worker logs to stdout via `logging.basicConfig(level=logging.INFO)`. In Docker, use `docker compose ... logs -f workers`.

### 7.5 Graceful shutdown and restart

- Stop with `Ctrl+C` (SIGINT).
- The worker has no custom signal handler; Python terminates the process.
- Restart by running the command again.
- Do not run two worker instances against the same database — they will compete for the same outbox rows (claiming reduces, but does not eliminate, duplicate work).

### 7.6 Development auto-reload (optional)

The worker has **no built-in reload**. For development, use `watchfiles`, which is already a dependency (`watchfiles==1.2.0`):

```bash
cd products/healthcare/dental/dentalpilot-ai/backend
source .venv/bin/activate
watchfiles --filter python --sigint-timeout 5 "python -m app.workers.run_workers" app
```

- `--filter python` watches only Python files.
- `--sigint-timeout 5` gives the worker 5 seconds to exit before force-killing.
- Stop the Compose `workers` service first to avoid duplicate workers:
  ```bash
  docker compose -f docker-compose.local.yml stop workers
  ```

### 7.7 Known limitation (observed)

If the database is unreachable or the schema is missing, each worker thread logs an exception and exits. The process does not restart dead threads. In production, Railway's restart policy (`ON_FAILURE`) restarts the process if it exits, but a single dead thread will not be revived while the others keep running. This is a robustness gap, not a configuration error; it is reported, not fixed here.

---

## 8. Local database and infrastructure

### 8.1 PostgreSQL (Docker)

`docker-compose.local.yml` starts:

- Container: `dentalpilot-local-postgres`
- Image: `postgres:16-alpine`
- Port: `5432`
- Database: `dentalpilot` (`POSTGRES_DB`)
- User: `dentalpilot` (`POSTGRES_USER`)
- Password: `POSTGRES_PASSWORD` from `.env.local`
- Volume: `postgres_local_data`
- Health check: `pg_isready`

Connection string:

```dotenv
# Inside Compose (backend container)
DATABASE_URL=postgresql+psycopg://dentalpilot:<POSTGRES_PASSWORD>@postgres:5432/dentalpilot

# From the host (native backend)
DATABASE_URL=postgresql+psycopg://dentalpilot:<POSTGRES_PASSWORD>@localhost:5432/dentalpilot
```

Verify:

```bash
docker compose -f docker-compose.local.yml exec postgres pg_isready -U dentalpilot -d dentalpilot
```

### 8.2 SQLite

- Default `DATABASE_URL=sqlite:///./dentalpilot.db`.
- File is created in `backend/`.
- Migrations: `alembic upgrade head`.
- **Known limitation:** the SQLite migration chain fails at `e78cbd0fad9c` (`Constraint must have a name`). Use PostgreSQL for a reliable local setup.

### 8.3 Redis

- `docker-compose.local.yml` starts `redis:7-alpine` on port `6379` with a `redis_local_data` volume.
- **The application does not use Redis.** There is no Redis client in `requirements.txt` and no `redis` import in `app/`. The workers are database-backed.
- Do not describe Redis as an active dependency; it is provisioned but unused.

---

## 9. Complete local startup sequence

### 9.1 Docker + PostgreSQL (recommended)

**Terminal 1 — infrastructure, backend and workers:**

```bash
cd products/healthcare/dental/dentalpilot-ai
cp .env.local.example .env.local
# Edit .env.local: POSTGRES_PASSWORD, JWT_SECRET, DATABASE_URL (host `postgres`)

docker compose -f docker-compose.local.yml up -d --build
docker compose -f docker-compose.local.yml ps
```

Compose starts, in order: `postgres` → `redis` → `migrate` (one-shot `alembic upgrade head`) → `backend` (Uvicorn with `--reload`) → `workers`.

**Terminal 2 — frontend:**

```bash
cd products/healthcare/dental/dentalpilot-ai/frontend
npm ci
npm start
```

> Do **not** start the backend or workers again in another terminal — Compose already runs them. Starting a native backend on `:8000` at the same time would conflict.

### 9.2 Native (SQLite or local PostgreSQL)

**Terminal 1 — database (optional, only if using PostgreSQL):**

```bash
docker run --name dentalpilot-native-postgres \
  -e POSTGRES_DB=dentalpilot \
  -e POSTGRES_USER=dentalpilot \
  -e POSTGRES_PASSWORD=<local password> \
  -p 5432:5432 -d postgres:16-alpine
```

If using SQLite, skip this terminal.

**Terminal 2 — backend:**

```bash
cd products/healthcare/dental/dentalpilot-ai/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: JWT_SECRET, DATABASE_URL
alembic upgrade head
python scripts/seed_hierarchy.py
uvicorn app.main:app --reload --reload-dir app --port 8000
```

**Terminal 3 — worker:**

```bash
cd products/healthcare/dental/dentalpilot-ai/backend
source .venv/bin/activate
python -m app.workers.run_workers
# Optional dev watcher:
# watchfiles --filter python --sigint-timeout 5 "python -m app.workers.run_workers" app
```

**Terminal 4 — frontend:**

```bash
cd products/healthcare/dental/dentalpilot-ai/frontend
npm ci
npm start
```

### 9.3 Terminal responsibilities

| Terminal | Docker workflow | Native workflow |
|---|---|---|---|
| 1 | `docker compose ... up -d --build` (DB + migrate + backend + workers) | Postgres (optional) |
| 2 | `npm start` (frontend) | Backend (`uvicorn --reload`) |
| 3 | — | Worker |
| 4 | — | Frontend (`npm start`) |

### 9.4 Local URLs

| Service | URL |
|---|---|
| Frontend | <http://localhost:4200> |
| Backend | <http://localhost:8000> |
| Swagger UI | <http://localhost:8000/docs> |
| Health | <http://localhost:8000/health> |
| Readiness | <http://localhost:8000/health/ready> |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` (unused) |

### 9.5 Shutdown, rebuild and logs

```bash
# Stop (keeps volumes)
docker compose -f docker-compose.local.yml stop

# Stop and remove containers (keeps volumes)
docker compose -f docker-compose.local.yml down

# Rebuild images
docker compose -f docker-compose.local.yml up -d --build

# Logs
docker compose -f docker-compose.local.yml logs -f backend workers

# Reset local data (DESTRUCTIVE — local volumes only)
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up -d --build
```

---

## 10. Troubleshooting

| Symptom | Check |
|---|---|
| Frontend cannot reach API | Backend on `:8000`; `CORS_ORIGINS` includes `http://localhost:4200` |
| `alembic upgrade head` fails on SQLite | Use Docker/PostgreSQL (Option A) |
| Backend starts but DB calls fail | `DATABASE_URL` correct; migrations applied |
| Worker logs `no such table` | Migrations not applied; run `alembic upgrade head` |
| Worker thread dies | Check DB connectivity; restart the worker; see §7.7 |
| Port already in use | `lsof -i :8000`, `lsof -i :4200`, `lsof -i :5432` |
| Compose starts duplicate services | You also started a native backend/worker; stop one |
| Frontend changes not picked up | Restart `npm start`; try `npm start -- --poll 1000` |
| Backend changes not picked up | Ensure `--reload-dir app`; restart for `.env`/dependency changes |

---

## 11. Related documentation

- [`README.md`](README.md) — overview and production deployment.
- [`ENVIRONMENT_GUIDE.md`](ENVIRONMENT_GUIDE.md) — environment variables and separation.
- [`RAILWAY_DEPLOYMENT.md`](RAILWAY_DEPLOYMENT.md) — production services.
- [`backend/README.md`](backend/README.md) — backend/worker details.
- [`frontend/README.md`](frontend/README.md) — frontend details.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution workflow.