# DentalPilot AI — Backend

> **ARCHIVED (historical).** Original backend document. The current AI provider is **Groq**; see `docs/notion/SETUP_AND_DEPLOYMENT.md` for current setup.

FastAPI backend implementing the REST contract the Angular frontend already expects (see `frontend/src/app/core/constants/api-endpoints.const.ts`). Every route, request/response shape, and error format is built to match the frontend exactly — including camelCase JSON, since the Angular app talks JSON straight off `HttpClient` with no transformation layer.

## Tech stack

- **FastAPI** + **Pydantic v2** — routing, validation, serialization
- **SQLAlchemy 2.0** + **Alembic** — ORM and migrations, against **SQLite** by default (swap `DATABASE_URL` for Postgres — the code doesn't change)
- **PyJWT** + **bcrypt** — auth (access/refresh JWTs, password hashing)
- **Anthropic SDK** — real AI content generation (Claude Opus 4.8, structured outputs, adaptive thinking)
- **Razorpay SDK** — real payments (Standard Checkout: order creation + signature-verified capture)

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set JWT_SECRET; set GROQ_API_KEY to enable AI (see docs/notion/SETUP_AND_DEPLOYMENT.md)
# content generation and RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET to enable payments (see below
# for both — the app runs fine without either, those two features just return a 503)

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The frontend's dev environment already points at `http://localhost:8000/api/v1`, so `npm start` in `frontend/` will talk to this out of the box.

## API endpoints

All endpoints are prefixed with `/api/v1` (e.g. `http://localhost:8000/api/v1/auth/login`). Interactive docs (Swagger UI) are at `http://localhost:8000/docs`; a plain health check is at `GET /health` (no prefix, no auth).

**Auth** — public

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create a clinic + user, returns tokens + user |
| POST | `/auth/login` | Returns tokens + user |
| POST | `/auth/refresh` | Exchange a refresh token for a new token pair |
| POST | `/auth/logout` | 204 — stateless, client discards tokens |
| POST | `/auth/forgot-password` | Always 204, regardless of whether the email exists |
| GET | `/auth/me` | 🔒 Current user |

**Clinic** — 🔒 requires `Authorization: Bearer <accessToken>`

| Method | Path | Description |
|---|---|---|
| GET | `/clinic/profile` | Current user's clinic profile |
| PUT | `/clinic/profile` | Update clinic profile |

**AI Content Generator** — 🔒

| Method | Path | Description |
|---|---|---|
| POST | `/content/generate` | Generate a post via Claude (503 if the former Anthropic API credential is unset) |
| GET | `/content` | List generated content for the clinic, newest first |
| GET | `/content/{content_id}` | Get one item |

**Content Calendar** — 🔒

| Method | Path | Description |
|---|---|---|
| GET | `/calendar/events` | List scheduled events |
| POST | `/calendar/events` | Schedule a piece of content |
| DELETE | `/calendar/events/{event_id}` | Remove an event (204, or 404) |

**Export** — 🔒

| Method | Path | Description |
|---|---|---|
| POST | `/export` | Create an export job (completes instantly, no file rendering) |
| GET | `/export` | List export jobs, newest first |

**Billing** — 🔒

| Method | Path | Description |
|---|---|---|
| GET | `/billing/plans` | The 4 static plan tiers (Free/Starter/Professional/Enterprise) |
| GET | `/billing/subscription` | Current clinic's plan, status, credits, renewal date |
| GET | `/billing/invoices` | Invoice history, newest first |
| POST | `/billing/razorpay/order` | Create a Razorpay order for a plan (or apply instantly if it's free) |
| POST | `/billing/razorpay/verify` | Verify a completed payment's signature, then apply the plan |

**Dashboard** — 🔒

| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/summary` | Aggregated counts, recent content, upcoming events |

## AI content generation

`POST /content/generate` calls the real Anthropic API (`claude-opus-4-8`, structured JSON output, adaptive thinking) using the clinic's profile (specialty, brand tone, target audience) as context, so generated copy matches each clinic's voice. **This requires the former Anthropic API credential to be set** — without it, the endpoint returns a clean `503` with an explanatory message (surfaced as a toast in the UI) rather than crashing.

## Payments (Razorpay Standard Checkout)

Upgrading a plan goes through a real Razorpay flow:

1. Frontend calls `POST /billing/razorpay/order` with the chosen plan/cycle. If the plan is free, the backend applies it immediately (Razorpay's minimum order is 100 subunits, so free plans skip payment entirely) and returns `{ requiresPayment: false, subscription }`. Otherwise it creates a real order via the Razorpay API, **persists what was actually ordered** (`PaymentOrder` row — plan, cycle, amount) keyed by the Razorpay order ID, and returns `{ requiresPayment: true, orderId, amount, currency, keyId }`.
2. Frontend opens Razorpay's `checkout.js` modal with those values.
3. On success, the frontend calls `POST /billing/razorpay/verify` with the three values Razorpay's modal returns (`razorpay_order_id`, `razorpay_payment_id`, `razorpay_signature`). The backend re-derives the expected signature via the Razorpay SDK (`HMAC-SHA256(order_id|payment_id, KEY_SECRET)`) and only applies the plan change if it matches.

**The plan/price applied on verify comes from the `PaymentOrder` row created in step 1, never from the verify request itself** — otherwise a client could pay for the cheapest plan and claim the most expensive one in the verify call. Verify is also idempotent (retrying with an already-paid order just returns the current subscription, no duplicate invoice) and a tampered signature is rejected with `400` **without** touching the clinic's plan.

This is Razorpay's Standard Checkout (one-time order + capture) — not their separate Subscriptions API, so there's no automatic renewal or webhook-driven billing cycle; each plan change is its own one-time charge.

Requires `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` in `.env` (test-mode keys work as-is); without them, both endpoints return a clean `503`. Currency is `RAZORPAY_CURRENCY` (default `USD`, matching the `$` prices shown in the UI) — confirmed working in Razorpay test mode, but Razorpay accounts are INR-primary and a **live** account typically needs "international payments" activated to accept non-INR orders; if that's not enabled, switch this to `INR` or contact Razorpay to activate it before going live.

## What's real vs. stubbed

| Area | Status |
|---|---|
| Auth (register/login/refresh/me) | Real — bcrypt password hashing, JWT access + refresh tokens |
| Clinic profile | Real — persisted per clinic |
| AI content generation | Real Claude API call, once the former Anthropic API credential is set |
| Content calendar | Real CRUD |
| Dashboard | Real aggregation queries against the database |
| Export (PDF/PNG/CSV) | Job records are real; actual file rendering is not implemented — jobs complete instantly with no `downloadUrl` |
| Billing / payments | Real Razorpay Standard Checkout (order creation + signature verification). No recurring billing/webhooks — see above |

## Known limitations

Gaps that exist in the current code, not just unbuilt features:

- **AI credit limits aren't enforced.** `Clinic.ai_credits_used` increments on every generation, but `POST /content/generate` never checks it against `ai_credits_limit` — a clinic can generate past its plan's cap with no error.
- **No email sending.** `POST /auth/forgot-password` always returns 204 but never sends a reset email, and there's no reset-token flow at all.
- **No JWT revocation.** `POST /auth/logout` is a no-op (stateless JWT); a leaked refresh token stays valid until it naturally expires.
- **Single user per clinic.** Registering always creates a brand-new clinic — there's no invite/team flow, so a clinic can't have more than one login.

## Project layout

```
app/
  core/        — config, database session, JWT/bcrypt security, auth dependency
  models/      — SQLAlchemy ORM models (Clinic, User, GeneratedContent, CalendarEvent, ExportJob,
                 Invoice, PaymentOrder)
  schemas/     — Pydantic request/response models — CamelModel base auto-converts to/from
                 the frontend's camelCase JSON (schemas use snake_case Python fields)
  routers/     — one module per frontend feature (auth, clinic, content, calendar, export, billing, dashboard)
  services/    — ai_content.py (Claude), razorpay_service.py (Razorpay), mappers.py (ORM → schema helpers)
alembic/       — migrations (versioned schema history)
```

A clinic owns its subscription/plan/AI-credit state directly (no separate `Clinic` vs `Subscription` split) since this app has one subscription per clinic — each `User` belongs to exactly one `Clinic`.

## Error format

All errors — `HTTPException`s and validation failures — are reshaped to match the frontend's `ApiErrorResponse` (`{ statusCode, message, errors? }`), which is what the Angular error interceptor reads to show toast notifications. FastAPI's default `{"detail": "..."}` shape would not match, so `app/main.py` registers custom exception handlers for this.

**Truly unhandled exceptions** (a genuine bug, not a deliberate `HTTPException`) are caught by `CatchAllExceptionMiddleware` in `app/main.py`, which logs the real exception server-side and returns the same `{statusCode: 500, message}` shape to the client. This middleware **must stay registered before `CORSMiddleware`** (i.e. `app.add_middleware(CatchAllExceptionMiddleware)` first, `app.add_middleware(CORSMiddleware, ...)` second). Reversing that order — or replacing the middleware with an `@app.exception_handler(Exception)` decorator — silently reintroduces a real bug: Starlette routes handlers registered for the base `Exception` class through `ServerErrorMiddleware`, which sits outside `CORSMiddleware`, so its response never gets CORS headers. In a browser, that means any unhandled backend bug shows up to the user as a misleading "Unable to reach the server" instead of the actual error.

## Database

SQLite by default (`dentalpilot.db`, gitignored). To use Postgres instead, set `DATABASE_URL=postgresql+psycopg://user:pass@host/db` in `.env` (note the `+psycopg` dialect suffix — the driver is already in `requirements.txt`) and re-run `alembic upgrade head`. No code changes needed either way.

Migrations:

```bash
alembic revision --autogenerate -m "description"   # after changing a model
alembic upgrade head                                 # apply
```

## Deployment (Railway)

Production runs on Railway at `api.dentalpilot.in`, on real Railway-provisioned Postgres (confirmed via the deploy log's `Context impl PostgresqlImpl` line — not the local SQLite fallback).

- **Root Directory**: `backend` (Railway → Service → Settings → Source) — the build context is already this folder, so nothing in the build/start pipeline should `cd backend`.
- **Start command**: owned entirely by `railway.toml`'s `[deploy].startCommand` — `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Migrations run automatically on every boot. **Never set a Custom Start Command in the Railway dashboard** — it silently overrides both `railway.toml` and `nixpacks.toml`, and caused a `cd: backend: No such file or directory` crash loop before this was caught.
- **Required environment variables** (Railway → Variables): `DATABASE_URL` (Postgres, `postgresql+psycopg://...`), `JWT_SECRET` (a real random value, never the `.env.example` default), `CORS_ORIGINS` (JSON array including the deployed frontend origin), `GROQ_API_KEY` (replaces the former Anthropic API credential), `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_CURRENCY`.
- **Custom domain**: `api.dentalpilot.in` → CNAME → the Railway-generated `*.up.railway.app` hostname, added at whichever DNS host manages `dentalpilot.in`. Railway issues the TLS cert automatically once the domain is verified and a deploy is live.
- **Status**: confirmed live — `curl https://api.dentalpilot.in/health` → `200 {"status":"ok"}`; `/docs` and real `/api/v1/...` routes also `200`; valid TLS; demo accounts seeded and persisted (see credentials below).

### Local vs. production — how they differ

There's no "switch" step — both configs exist side by side and are picked automatically based on how you run things. Editing local `.env` has zero effect on production, and vice versa.

| | Local | Production |
|---|---|---|
| URL | `http://localhost:8000/api/v1` | `https://api.dentalpilot.in/api/v1` |
| Database | SQLite file (`dentalpilot.db`, gitignored) | Real Postgres, Railway-managed, persists across deploys |
| Config source | `backend/.env` (gitignored, edit directly, restart `uvicorn` to pick up changes) | Railway → service → **Variables** tab, or `railway variable set` via CLI (auto-redeploys) |
| JWT secret | dev placeholder | real random secret |
| Frontend it talks to | `frontend/src/environments/environment.ts` (`localhost:4200`) | `environment.prod.ts` (`staging.dentalpilot.in`) |
| Seeding demo accounts | `python scripts/seed_hierarchy.py` (run directly, uses local `.env`) | same script, run once via `railway ssh -- /opt/venv/bin/python scripts/seed_hierarchy.py` (already done) |

### Pushing to production

Production auto-deploys from GitHub — there's no separate "deploy" command:

1. `git push` to `main` (Railway → Settings → Source → "Branch connected to production" — currently `main`).
2. Railway's webhook fires and starts a new build automatically.
3. It builds per `backend/nixpacks.toml` and starts per `backend/railway.toml`'s `startCommand` (migrations run on every deploy), using whatever's currently set in the Variables tab.
4. Watch it land — dashboard: Deployments tab; CLI (after `railway link`): `railway logs --deployment --lines 40`.
5. **Always confirm the deploy actually picked up your latest commit** before assuming a fix is live: deployment card → **Details** tab → check the commit message/SHA under "Deployed via GitHub". A stale deploy can silently keep serving an old commit if the webhook didn't fire — this happened once already, and cost real debugging time before it was caught.
6. Sanity check from anywhere: `curl https://api.dentalpilot.in/health` → expect `{"status":"ok"}`.

The frontend isn't wired to auto-deploy anywhere yet, so this push-to-deploy flow currently only applies to the backend.

### Troubleshooting (real incidents hit getting this live)

- **Same crash persists after pushing a fix.** Check the deployment's **Details** tab for the actual commit SHA before re-debugging the code — if it doesn't match the latest push, the fix was never deployed. Force a fresh one via Settings → Source → disconnect/reconnect GitHub, or a manual "Deploy" targeting `main`.
- **Build fails with `/root/.nix-profile/bin/python: No module named pip`.** A custom `[phases.install]` in `nixpacks.toml` that manually runs `python -m pip install --upgrade pip` can fail because the bare `python311` Nix package doesn't always bundle `pip`. Fix: don't override `[phases.install]` at all — Nixpacks' built-in Python installer already creates a venv with `pip` via `ensurepip` and installs reliably on its own.

### Production login credentials

Seeded once directly against production Postgres (persists across deploys — these are demo/test accounts, replace before real users sign up):

| Role | Email | Password |
|---|---|---|
| Super Admin | `super-admin@dentalpilot.ai` | `password123` |
| Owner | `owner@brightsmiledental.io` | `password123` |
| Staff | `staff@brightsmiledental.io` | `password123` |
