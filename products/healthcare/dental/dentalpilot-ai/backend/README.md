# DentalPilot AI — Backend

FastAPI backend implementing the REST contract the Angular frontend already expects (see [`../frontend/src/app/core/constants/api-endpoints.const.ts`](../frontend/src/app/core/constants/api-endpoints.const.ts)). Every route, request/response shape, and error format is built to match the frontend exactly — including camelCase JSON, since the Angular app talks JSON straight off `HttpClient` with no transformation layer.

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
# edit .env: set JWT_SECRET to a real random string; set ANTHROPIC_API_KEY to enable AI
# content generation and RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET to enable payments (see below
# for both — the app runs fine without either, those two features just return a 503)

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The frontend's dev environment (`frontend/src/environments/environment.ts`) already points at `http://localhost:8000/api/v1`, so `npm start` in `frontend/` will talk to this out of the box.

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

**Clinic** — most routes require `Authorization: Bearer <accessToken>`; invitation acceptance is public with a one-time token

| Method | Path | Description |
|---|---|---|
| GET | `/clinic/profile` | Current user's clinic profile |
| PUT | `/clinic/profile` | Update clinic profile |
| GET | `/clinic/branches` | List branches visible to the current staff member |
| POST | `/clinic/branches` | Create a branch (owner only) |
| GET | `/clinic/staff` | List clinic staff |
| POST | `/clinic/staff/invitations` | Issue a one-time branch-scoped invitation (owner only) |
| POST | `/clinic/staff/invitations/accept` | Activate a staff account with an invitation token |
| GET | `/clinic/onboarding` | Read clinic setup status |
| POST | `/clinic/onboarding/complete` | Mark setup complete (owner only) |

**Healthcare workflows** — 🔒 clinic-scoped

| Method | Path | Description |
|---|---|---|
| POST/GET | `/healthcare/patients` | Create/list patients; staff visibility is branch-scoped |
| POST/GET | `/healthcare/treatment-plans` | Create/list treatment plans and stages |
| PATCH | `/healthcare/treatment-stages/{stage_id}` | Record permitted decisions and lifecycle changes |
| GET | `/healthcare/patients/{patient_id}/decisions` | Review patient decision history |
| GET | `/healthcare/revenue-recovery` | Treatment estimates plus clinic-entered charges, payments, refunds, net collected, and outstanding balance |
| POST/GET | `/healthcare/treatment-ledger` | Record and list clinic-entered treatment charges, payments, and refunds |
| POST/GET | `/healthcare/visits` | Record and list appointments, completed visits, cancellations, and no-shows |
| GET | `/healthcare/analytics?from_date=...&to_date=...` | Date-filtered treatment, recall, visit, retention, and enquiry metrics (maximum 366 days) |
| POST/GET/PATCH | `/healthcare/records` | Add/list/correct records with versioned provenance |
| POST | `/healthcare/records/{record_id}/file` | Upload a validated private PDF/JPEG/PNG/WebP document to configured object storage |
| GET | `/healthcare/records/{record_id}/download` | Download a stored record file with clinic/branch authorization |
| GET | `/healthcare/records/{record_id}/revisions` | Read correction history |
| POST/GET | `/healthcare/consents` | Grant/list scoped patient-record consent |
| POST | `/healthcare/consents/{consent_id}/revoke` | Revoke consent and dependent share links |
| POST/GET/PATCH | `/healthcare/reminders` | Create/list/update consent-confirmed reminders |
| POST | `/healthcare/reminders/{reminder_id}/approve` | Confirm consent and enqueue an automated reminder email |
| GET/PUT | `/healthcare/recall-settings` | Read/update post-treatment, deferred-treatment, and hygiene recall intervals (owner updates) |
| POST | `/healthcare/patients/{patient_id}/email` | Queue an individual consent-confirmed patient email |
| GET | `/healthcare/email-outbox` | Inspect pending/sent/failed clinic email delivery status |
| GET | `/healthcare/audit` | Read clinic audit events |
| POST/GET | `/healthcare/integrations` | Store provider-neutral integration metadata |
| POST | `/healthcare/integrations/csv/import` | Map CSV columns and import patient rows |
| GET | `/healthcare/integrations/csv/export` | Export branch-visible patient data as CSV |
| GET | `/healthcare/integrations/sync-jobs` | Read import/export job results and row errors |

**Dental operations** — 🔒 clinic/branch-scoped; these are native tracking workflows, not device integrations

| Method | Path | Description |
|---|---|---|
| POST/GET/PATCH | `/operations/dental-cases` | Coordinate imaging, scanner, lab, CAD/CAM, 3D-print, implant, and robotics cases with guarded lifecycle states |
| POST/GET | `/operations/dental-cases/{case_id}/events` | Record and read case milestones, handoffs, approvals, and notes |
| POST/GET/PATCH | `/operations/assets` | Register clinic equipment and track status/service dates |
| POST/GET/PATCH | `/operations/assets/{asset_id}/maintenance` | Record maintenance, breakdowns, repairs, and calibration work |
| POST/GET | `/operations/sterilization-cycles` | Manually log autoclave cycles; failed cycles mark the asset unavailable |
| POST/GET/PATCH | `/operations/message-drafts` | Prepare consent-confirmed email/SMS/WhatsApp drafts; approval does not send them |
| POST/GET/PATCH | `/operations/marketing-publications` | Plan, approve, schedule, and manually record publication status; no external publishing occurs |
| POST/GET | `/operations/clinical-note-drafts` | Save/list clinician-entered note drafts; no AI text generation |
| PATCH | `/operations/clinical-note-drafts/{draft_id}/review` | Approve or reject a draft |
| GET | `/integrations/catalog` | List the enabled CSV exchange and disabled future provider candidates |

**Clinic organizations** — 🔒 clinic owners

| Method | Path | Description |
|---|---|---|
| GET | `/organizations/current` | Read the current optional clinic group (null when standalone) |
| POST | `/organizations` | Create a clinic group for the current clinic |
| GET | `/organizations/current/analytics` | Aggregate clinic, branch, patient, treatment-stage, visit, and ledger totals; financial values stay grouped by native currency with no FX conversion |
| GET | `/organizations/current/members` | List member clinics and roles (organization owner/admin) |
| PATCH | `/organizations/current/members/{user_id}/role` | Set a member to organization admin or reporting-only (organization owner) |
| DELETE | `/organizations/current/members/{user_id}` | Remove a member clinic without deleting clinic data (organization owner) |
| POST | `/organizations/current/invitations` | Create a one-time clinic-owner invitation (owner/admin; manual secure delivery) |
| POST | `/organizations/invitations/accept` | Join as reporting-only; requires a signed-in clinic owner matching the invited email |

**Patient portal** — invitation activation and login are public; patient records require a patient token

| Method | Path | Description |
|---|---|---|
| POST | `/patient-portal/invitations` | Clinic staff issues a one-time patient invitation |
| POST | `/patient-portal/invitations/accept` | Patient activates account with a password |
| POST | `/patient-portal/login` | Patient-only access token |
| GET | `/patient-portal/me` | Patient profile |
| GET | `/patient-portal/records` | List the signed-in patient's records |
| GET | `/patient-portal/records/{record_id}/download` | Download the patient's stored file, or metadata JSON when no file is attached |
| POST | `/patient-portal/shares` | Create an expiring view-only share |
| GET | `/patient-portal/shares/{share_token}` | View records through a share token |
| GET | `/billing/treatment-payments/portal/charges` | List this patient's outstanding charge balances |
| POST | `/billing/treatment-payments/portal/orders` | Start a Razorpay checkout for this patient's own charge |
| POST | `/billing/treatment-payments/portal/verify` | Verify a captured payment using the patient-only token |

**AI Content Generator** — 🔒

| Method | Path | Description |
|---|---|---|
| POST | `/content/generate` | Generate a post via Claude (503 if `ANTHROPIC_API_KEY` unset) |
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
| POST | `/export` | Create an export job — renders a real CSV/PDF/PNG (zipped for multi-item PNG) to disk and sets `downloadUrl` |
| GET | `/export` | List export jobs, newest first |
| GET | `/export/{job_id}/download` | Download the rendered file (blob, clinic-scoped) |

**Billing** — 🔒

| Method | Path | Description |
|---|---|---|
| GET | `/billing/plans` | The 4 static plan tiers (Free/Starter/Professional/Enterprise) |
| GET | `/billing/subscription` | Current clinic's plan, status, credits, renewal date |
| GET | `/billing/invoices` | Invoice history, newest first |
| POST | `/billing/subscriptions` | Create a Razorpay Subscription checkout (or apply the free plan) |
| POST | `/billing/subscriptions/verify` | Verify the initial subscription authorization signature |
| POST | `/billing/subscriptions/cancel` | Cancel now or at the end of the current cycle |
| POST | `/billing/razorpay/subscriptions/webhook` | Receive signed Razorpay subscription lifecycle events |

**Dashboard** — 🔒

| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/summary` | Aggregated counts, recent content, upcoming events |

## AI content generation

`POST /content/generate` calls the real Anthropic API (`claude-opus-4-8`, structured JSON output, adaptive thinking) using the clinic's profile (specialty, brand tone, target audience) as context, so generated copy matches each clinic's voice. **This requires `ANTHROPIC_API_KEY` to be set** — without it, the endpoint returns a clean `503` with an explanatory message (surfaced as a toast in the UI) rather than crashing.

## Payments (Razorpay Standard Checkout)

Upgrading a plan goes through a real Razorpay flow:

1. The frontend calls `POST /billing/subscriptions` with the chosen paid plan and cycle. The API creates a Razorpay Subscription using the server-configured plan ID and returns its `subscription_id`; the free plan is applied without a payment step.
2. The frontend passes that ID as `subscription_id` to Razorpay Checkout. It then sends the authorization response to `POST /billing/subscriptions/verify`. The server verifies `HMAC-SHA256(payment_id|subscription_id, KEY_SECRET)` using the subscription ID it created, not a client-selected plan.
3. Razorpay sends signed lifecycle events to `POST /api/v1/billing/razorpay/subscriptions/webhook`. Receipt is idempotent and durable; `python -m app.workers.subscription_billing` reconciles provider state, invoices, renewal credit resets, failures, grace periods, and cancellation.

Set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, and `RAZORPAY_PLAN_IDS` (all paid tiers, monthly and annual) in deployment secrets. Deploy a separate Railway worker service using the same repository, `backend` root directory, and start command `python -m app.workers.run_workers`; it runs subscription reconciliation and the SMTP outbox. The web service only stores events and must not be the only deployed process.

## Treatment payments, insurance claims, accounting, and PMS reconciliation

These are separate from the clinic's subscription checkout:

- Staff can start a Razorpay Standard Checkout for an outstanding treatment charge from Revenue Recovery. The server calculates the balance and enforces `PATIENT_PAYMENT_CURRENCY` (default `INR`); a successful, signature-verified capture is recorded once as a payment linked to its charge. Razorpay test credentials are supported. Configure `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `PATIENT_PAYMENT_CURRENCY` in deployment secrets; the charge currency must match the configured payment currency.
- Signed-in patients can also view and pay their own outstanding charges from the patient portal. The portal token is scoped to the patient and clinic; patients cannot select another patient's charge. Razorpay credentials and currency requirements are the same.
- The signed `POST /api/v1/billing/razorpay/webhook` endpoint handles `payment.captured` events. Configure its URL in Razorpay and set the matching `RAZORPAY_WEBHOOK_SECRET` in deployment secrets. Verification from the checkout is also supported; duplicate webhook/verification delivery does not create duplicate ledger payments.
- Revenue Recovery provides clinic/branch-scoped, audited CSV exports for the treatment ledger and insurance claims. These are interoperable files, not automatic posting or reconciliation with an accounting provider.
- Staff can manually track insurance claim submission, payer decisions, approvals, denials, and remittances. Recorded payer remittances are added to the patient ledger; claim data is not submitted to an insurer or clearinghouse.
- PMS transaction reconciliation accepts a provider-neutral CSV with a configurable mapping for transaction reference, patient reference, entry type, amount, and currency. It stores run summaries and row-level matched, mismatched, missing, duplicate, and invalid results. No vendor API, automatic import, or bidirectional sync is included.

Live provider credentials and production settlement were not exercised in tests. Use Razorpay test mode first and reconcile provider settlement reports before enabling live checkout.

## What's real vs. stubbed

| Area | Status |
|---|---|
| Auth (register/login/refresh/me) | Real — bcrypt password hashing, JWT access + refresh tokens |
| Clinic profile | Real — persisted per clinic |
| AI content generation | Real Claude API call, once `ANTHROPIC_API_KEY` is set |
| Content calendar | Real CRUD |
| Dashboard | Real aggregation queries against the database |
| Export (PDF/PNG/CSV) | Real — CSV (stdlib), PDF (`reportlab`, paginated), PNG (`Pillow`, zipped when exporting multiple items), stored on local disk, downloaded via an authenticated blob endpoint |
| Billing / payments | Razorpay Subscriptions for SaaS billing with signed webhooks and reconciliation; Razorpay Standard Checkout for treatment charges. Captured treatment payments enter the charge-linked ledger. |
| Roles / permissions | Real — `super_admin` / `owner` / `staff` hierarchy, enforced server-side (see below) |
| Healthcare workflows | MVP implementation — branch-scoped clinic operations, patient self-service treatment payments, manual insurance claims, accounting CSV exports, PMS CSV reconciliation, patient visit and retention metrics, patient portal, scoped consent, provenance revisions, recall approval queue, and audit |
| Digital dentistry / equipment | Native manual case tracking, maintenance, and sterilisation logs; no DICOM viewer, device telemetry, hardware connection, or robotic control |
| Clinic groups | Optional organization roles and aggregate operational/financial reporting by native currency; no FX conversion, patient-level sharing, or standalone-clinic restriction |
| Patient document storage | Real S3-compatible uploads/downloads when configured; files are validated, size-limited, private, and server-side encrypted |
| Patient email delivery | Real SMTP outbox and retry worker when configured; automated recall messages require staff consent verification and approval |

## Roles

Every `User` has a `role`: `super_admin`, `owner`, or `staff`. Registering through `/auth/register` creates a clinic owner. Owners can invite staff to a specific branch; invitation delivery is manual because no email provider is configured.

| Role | Scope | Can do |
|---|---|---|
| `staff` | Assigned clinic branch | Clinic workflows, treatment charges/payments, claims, scoped exports, and PMS CSV reconciliation; subscription billing and clinic profile edits return `403` |
| `owner` | One clinic | Everything `staff` can, plus edit clinic profile and manage billing |
| `super_admin` | All clinics | Everything `owner` can for their own clinic, plus `GET /admin/clinics` — a platform-wide list, not scoped by `clinic_id` |

Enforcement is server-side — `PUT /clinic/profile` and subscription checkout under `/billing/razorpay/*` require `owner` or higher; treatment payment, claims, accounting export, and PMS reconciliation routes require clinic staff and enforce clinic/branch scope. `/admin/clinics` requires `super_admin`. Note the cross-clinic visibility is scoped to that one admin endpoint — regular endpoints (content, calendar, dashboard, etc.) still filter by the caller's own `clinic_id` even for a `super_admin`.

`python scripts/seed_hierarchy.py` creates one demo clinic with a login at each level (password `password123` for all three) — see the script for the exact emails. Staff accounts must have a branch assignment; the migrations assign existing clinic staff to their clinic's primary branch.

## Known limitations

Gaps that exist in the current code, not just unbuilt features:

- **Email is limited to patient workflow messages.** The SMTP outbox does not send password resets or staff/patient invitations; those flows still require secure manual delivery.
- **No JWT revocation.** `POST /auth/logout` is a no-op (stateless JWT); a leaked refresh token stays valid until it naturally expires.
- **External storage is opt-in.** Configure an S3-compatible bucket before enabling file uploads. The app enforces clinic/branch authorization and uses clinic-scoped object keys; bucket access must remain private and backups/retention must be configured by the operator.
- **Treatment payment coverage is limited.** Razorpay checkout supports configured treatment charges; refunds and adjustments remain staff-entered. There is no accounting-provider posting, payment terminal integration, subscription renewal webhook, or settlement reconciliation.
- **Insurance remains manual.** Claim status and payer remittances can be tracked, but claims are not transmitted to insurers/clearinghouses and eligibility is not checked.
- **PMS reconciliation is CSV-only.** It compares mapped transaction exports with the local ledger; vendor-specific connectors, automatic import, and bidirectional sync are not configured.
- **Marketing remains manual.** Listing checks, campaigns, and review-response drafts are not published or synchronized with external platforms.
- **Limited portal lifecycle.** Patient accounts support invitation activation and login, but not password reset, email delivery, or refresh-token revocation.

## Private documents and patient email

The app's AWS SDK uses its normal credential chain (for example, an attached cloud-service role or local AWS profile). Do not put cloud credentials in source control or commit them to `.env.example`.

- Set `S3_BUCKET` and `AWS_REGION`; optionally set `S3_ENDPOINT_URL` for an S3-compatible provider or `S3_KMS_KEY_ID` to use KMS instead of the default `AES256` server-side encryption.
- Keep public access blocked and grant the app identity only the required bucket/object operations. Configure bucket versioning, lifecycle/retention, and tested backups according to the clinic's records policy. Object keys are clinic/patient/record scoped; application authorization remains the access boundary.
- `MAX_PATIENT_DOCUMENT_BYTES` defaults to 25,000,000 bytes. Uploads accept validated PDF, JPEG, PNG, and WebP files only.
- Set `SMTP_HOST`, `SMTP_PORT`, and `SMTP_SENDER_EMAIL`; configure credentials only through environment/secret management. Select one transport security mode (`SMTP_USE_SSL` for implicit TLS or `SMTP_USE_STARTTLS` for STARTTLS). `SMTP_USERNAME` and `SMTP_PASSWORD` must be configured together.
- Run the durable workers as a separate process/service against the same database and environment: `python -m app.workers.run_workers`. The web process does not send queued messages itself. Retries use capped exponential backoff and stop at `EMAIL_MAX_ATTEMPTS`.
- Automated recall events create `pending-approval` reminders; a clinic owner configures the intervals and authorized staff explicitly confirm email consent before a reminder enters the outbox. The worker must be monitored and restarted by the deployment platform.
- Provider delivery/storage cannot be verified without clinic-controlled provider credentials. Tests should use fakes/mocks and must not require live accounts or secrets.

## Project layout

```
app/
  core/        config, database session, JWT/bcrypt security, auth dependency
  models/      SQLAlchemy ORM models (clinic, healthcare, content, billing, and export entities)
  schemas/     Pydantic request/response models — CamelModel base auto-converts to/from
               the frontend's camelCase JSON (schemas use snake_case Python fields)
  routers/     feature modules (auth, clinic, healthcare, patient portal, content, calendar, export,
               billing, dashboard)
  services/    ai_content.py (Claude), razorpay_service.py (Razorpay), document_storage.py (S3-compatible
               storage), email_delivery.py (SMTP), export_render.py (CSV/PDF/PNG rendering)
  workers/     email_outbox.py and subscription_billing.py (durable workers); run_workers.py (worker-service entry point)
alembic/       migrations (versioned schema history)
```

A clinic owns its subscription/plan/AI-credit state directly (no separate `Clinic` vs `Subscription` split) since this app has one subscription per clinic — each `User` belongs to exactly one `Clinic`.

## Error format

All errors — `HTTPException`s and validation failures — are reshaped to match the frontend's `ApiErrorResponse` (`{ statusCode, message, errors? }`), which is what the Angular error interceptor reads to show toast notifications. FastAPI's default `{"detail": "..."}` shape would not match, so `app/main.py` registers custom exception handlers for this.

**Truly unhandled exceptions** (a genuine bug, not a deliberate `HTTPException`) are caught by `CatchAllExceptionMiddleware` in `app/main.py`, which logs the real exception server-side and returns the same `{statusCode: 500, message}` shape to the client. This middleware **must stay registered before `CORSMiddleware`** (i.e. `app.add_middleware(CatchAllExceptionMiddleware)` first, `app.add_middleware(CORSMiddleware, ...)` second). Reversing that order — or replacing the middleware with an `@app.exception_handler(Exception)` decorator — silently reintroduces a real bug: Starlette routes handlers registered for the base `Exception` class through `ServerErrorMiddleware`, which sits *outside* `CORSMiddleware`, so its response never gets CORS headers. In a browser, that means any unhandled backend bug shows up to the user as a misleading "Unable to reach the server" instead of the actual error. See the docstring on `CatchAllExceptionMiddleware` for the full explanation.

## Database

SQLite by default (`dentalpilot.db`, gitignored). To use Postgres instead, set `DATABASE_URL=postgresql+psycopg://user:pass@host/db` in `.env` (note the `+psycopg` dialect suffix — the driver is already in `requirements.txt`) and re-run `alembic upgrade head`. No code changes needed either way.

Migrations:

```bash
alembic revision --autogenerate -m "description"   # after changing a model
alembic upgrade head                                 # apply
```

## Deployment (Railway)

Production runs on Railway at `api.dentalpilot.in`.

- **Root Directory**: `backend` (set in Railway → Service → Settings → Source) — the build context is already this folder, so nothing in the build/start pipeline should `cd backend`.
- **Start command**: owned entirely by `railway.toml`'s `[deploy].startCommand` — `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Migrations run automatically on every boot. **Do not set a Custom Start Command in the Railway dashboard** — a dashboard override silently takes priority over both `railway.toml` and `nixpacks.toml`, which is what caused a `cd: backend: No such file or directory` crash loop before this was documented.
- **Required environment variables** (Railway → Variables): `DATABASE_URL` (Postgres, `postgresql+psycopg://...`), `JWT_SECRET` (a real random value — never the `.env.example` default), `CORS_ORIGINS` (JSON array including the deployed frontend origin, e.g. `["https://staging.dentalpilot.in"]`), `ANTHROPIC_API_KEY`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_CURRENCY`.
- **Custom domain**: `api.dentalpilot.in` → CNAME → the Railway-generated `*.up.railway.app` hostname, added at whichever registrar/DNS host manages `dentalpilot.in`. Railway issues the TLS cert automatically once the domain is verified and a deploy is live.
- **Health check**: `GET /health` → `{"status": "ok"}`, used by Railway's own healthcheck (`healthcheckPath` in `railway.toml`) and safe to curl manually to confirm the service is up.
- **Status**: confirmed live — `curl https://api.dentalpilot.in/health` returns `200 {"status":"ok"}`, `/docs` and real `/api/v1/...` routes also confirmed `200`, valid TLS, routed through Railway's edge. Running on a real Railway-provisioned Postgres (not the local SQLite fallback) — confirmed via the deploy log's `Context impl PostgresqlImpl` line. Demo accounts are seeded and persist across deploys (see credentials below).

### Viewing logs

- **Local**: `uvicorn --reload` prints request logs and tracebacks straight to the terminal you ran it in — nothing extra to configure.
- **Production**: Railway → the service → **Deployments** tab → click a deployment card → four sub-tabs:
  - **Build Logs** — install/build phase output (Nixpacks steps, `pip install`, image push).
  - **Deploy Logs** — runtime output: `alembic upgrade head` migration lines, then Uvicorn's own startup/request logs (`app.logger`'s `logger.exception(...)` calls from `main.py`'s `CatchAllExceptionMiddleware` show up here too).
  - **Network Logs** — per-request edge log (path, HTTP status, duration) — useful for spotting `502`/`499`s from outside without needing app-level logging.
  - **Details** — shows which exact git commit this deployment built from ("Deployed via GitHub" section). Check this first whenever a fix doesn't seem to be taking effect — see below.

### Troubleshooting (real incidents hit getting this live)

- **Same crash persists after pushing a fix.** Railway's "Active" deployment card can silently still be running an old commit if a push didn't trigger a redeploy (webhook hiccup, or a manual "Redeploy" click reusing an old build instead of pulling latest). Always check that deployment's **Details** tab for the actual commit message/SHA before re-debugging the code — if it doesn't match your latest push, the fix was never deployed. Force a fresh one via Settings → Source → disconnect/reconnect GitHub, or a manual "Deploy" from the Deployments tab targeting `main`.
- **Build fails with `/root/.nix-profile/bin/python: No module named pip`.** A custom `[phases.install]` in `nixpacks.toml` that manually runs `python -m pip install --upgrade pip` can fail because the bare `python311` Nix package doesn't always bundle `pip`. Fix: don't override `[phases.install]` at all — Nixpacks' built-in Python installer already creates a venv with `pip` via `ensurepip` and runs `pip install -r requirements.txt` reliably on its own.

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
3. It builds per `backend/nixpacks.toml` and starts per `backend/railway.toml`'s `startCommand` (`alembic upgrade head && uvicorn ...` — migrations run on every deploy), using whatever's currently set in the Variables tab.
4. Watch it land — dashboard: Deployments tab; CLI (after `railway link`): `railway logs --deployment --lines 40`.
5. **Always confirm the deploy actually picked up your latest commit** before assuming a fix is live: deployment card → **Details** tab → check the commit message/SHA under "Deployed via GitHub". A stale deploy can silently keep serving an old commit if the webhook didn't fire — this happened once already (see Troubleshooting above), and cost real debugging time before it was caught.
6. Sanity check from anywhere: `curl https://api.dentalpilot.in/health` → expect `{"status":"ok"}`.

The frontend isn't wired to auto-deploy anywhere yet, so this push-to-deploy flow currently only applies to the backend.

### Production login credentials

Seeded once directly against production Postgres (persists across deploys — these are demo/test accounts, replace before real users sign up):

| Role | Email | Password |
|---|---|---|
| Super Admin | `super-admin@dentalpilot.ai` | `password123` |
| Owner | `owner@brightsmiledental.io` | `password123` |
| Staff | `staff@brightsmiledental.io` | `password123` |
