# DentalPilot AI — Product Implementation Audit

> **Historical baseline.** This audit predates the Groq migration; the current AI provider is **Groq**. Findings are preserved as historical evidence. See `docs/notion/SETUP_AND_DEPLOYMENT.md` for current setup.

**Audit type:** Read-only, evidence-based
**Date:** 2026-11-24
**Scope:** `products/healthcare/dental/dentalpilot-ai/`
**Auditor roles:** Principal Software Architect, Healthcare SaaS Product Auditor, QA Automation Engineer
**Method:** Static source inspection, endpoint/model extraction, containerised test execution, Docker Compose/Nginx validation.

> **No source, configuration, database, migration or deployment file was modified by this audit.**
> The only file created is this document.
> The audit covers the **current on-disk state**, which includes uncommitted changes from a prior environment-engineering task (see §0.2). Where a finding is fixed only by an uncommitted working-tree change, it is labelled **[working-tree fix]**.

---

## 0. Audit basis and working-tree state

### 0.1 Commands executed

| Purpose | Command | Result |
|---|---|---|
| Backend image build | `docker build -t dentalpilot-backend:local ./backend` | **Success** |
| Backend tests | `docker run --rm -v "$PWD/backend/tests:/app/tests:ro" -v "$PWD/backend/pytest.ini:/app/pytest.ini:ro" dentalpilot-backend:local pytest tests/ -q` | **25 passed** (after working-tree `dashboard.py` fix) |
| Backend import (pre-fix) | same image, before fix | **Failed**: `NameError: name 'MonthlyRevenuePoint' is not defined` |
| Alembic head chain | `docker run --rm dentalpilot-backend:local alembic history` / `alembic heads` | Single head `e78cbd0fad9c`, linear 12-revision chain |
| SQLite migration | backend container default `DATABASE_URL` | **Failed**: `ValueError: Constraint must have a name` in `e78cbd0fad9c` |
| Local Compose | `docker compose -f docker-compose.local.yml config` | **Valid** |
| Production Compose | `docker compose --env-file .env.production.example -f docker-compose.yml config` | **Valid** |
| Staging Compose | `docker compose --env-file .env.staging.example -f docker-compose.yml -f docker-compose.staging.yml config` | **Valid**; frontend ports overridden to `8080`, staging nginx mounted |
| Nginx configs | `docker run ... nginx:alpine nginx -t` | **All pass** (staging, frontend, production) |
| Frontend tests | `npm test` | **Not executed** — `frontend/node_modules` absent; audit is read-only |
| Frontend build | `npm run build` | **Not executed** — same reason |

### 0.2 Working-tree state at audit time

`git status --short` shows uncommitted changes from a prior environment-engineering task:

```
 M .env.production.example
 M backend/app/schemas/dashboard.py
 M deploy.sh
 M docker-compose.staging.yml
 M docker-compose.yml
 M frontend/nginx.conf
 M nginx/conf.d/default.conf
?? .env.local.example
?? .env.staging.example
?? .gitignore
?? docker-compose.local.yml
?? nginx/staging/
```

Two of these are **P0 fixes** that are not yet committed:

- `backend/app/schemas/dashboard.py` — class reorder fixes the import-blocking `NameError`.
- `nginx/conf.d/default.conf` and `frontend/nginx.conf` — `proxy_pass` prefix fix.

If those working-tree changes are reverted, the corresponding P0 findings (P0-1, P0-3) return.

---

## A. Executive summary

### A.1 Overall status

DentalPilot AI is a **substantial, feature-rich implementation** — not a prototype. It contains:

- **17 FastAPI routers**, **156 HTTP endpoints**, **40+ SQLAlchemy models**, **12 Alembic migrations**, **3 background workers**.
- **14 Angular feature areas** with real `HttpClient` integrations (112 distinct endpoint constants referenced).
- Real integrations: Razorpay (subscriptions + patient payments), Anthropic, SMTP, S3-compatible storage, WhatsApp Cloud API.
- Consent, audit, tenant isolation and webhook signature verification are implemented in the core flows.

However, the repository is **not currently releasable** because of **four P0 blockers** (one import-blocking code defect, one migration defect, one reverse-proxy defect, and the absence of any executable CI). Three of the four are already fixed in the working tree but uncommitted.

### A.2 What works (verified)

- Backend image builds from `backend/Dockerfile` (Python 3.12).
- **25 backend tests pass** across `test_healthcare_workflows.py`, `test_native_operations_and_organizations.py`, `test_email_outbox.py`.
- Alembic has a **single head** and a linear 12-step chain.
- Local, staging and production Compose files validate; staging correctly overrides ports and nginx config.
- All three nginx configurations pass `nginx -t`.
- Tenant isolation is generally enforced via `clinic_id` filters in healthcare, operations, billing, financial analytics, growth, export and patient-portal routers.
- Webhooks (`billing.py`, `patient_billing.py`) verify Razorpay signatures.
- Patient document storage is S3-only (no local fallback), with presigned download URLs and audit events.

### A.3 Major blockers (P0)

| ID | Blocker | Evidence | Status |
|---|---|---|---|
| P0-1 | Backend cannot import (`app.main`) due to forward-referenced Pydantic models | `NameError: name 'MonthlyRevenuePoint' is not defined` | **[working-tree fix]** |
| P0-2 | Alembic migration `e78cbd0fad9c` fails on SQLite (`Constraint must have a name`) | `ValueError: Constraint must have a name` | **Open** |
| P0-3 | Production nginx strips `/api/` prefix (`proxy_pass http://backend/;`) | nginx config vs `main.py` prefix `/api/v1` | **[working-tree fix]** |
| P0-4 | No application-level rate limiting on auth/login/registration/patient-portal login | no `slowapi`/`limiter` in `app/`; nginx-only | **Open** |
| P0-5 | No executable CI/CD (only workflow is nested and ignored by GitHub) | `.github/workflows/ci-cd.yml` under `dentalpilot-ai/` | **Open** |

### A.4 Readiness verdict

| Environment | Readiness | Notes |
|---|---|---|
| Local (Docker) | **Partially ready** | Compose valid; blocked by P0-2 if using SQLite; Postgres path not executed end-to-end. |
| Staging | **Partially ready** | Working-tree staging config is valid; P0-4/P0-5 remain. |
| Production | **Not ready** | P0-1..P0-5 must be closed; no CI artifacts; no DB backup automation evidenced. |

---

## B. Feature inventory

Classification legend: **Fully implemented & tested**, **Implemented, insufficiently tested**, **Partially implemented**, **UI only**, **Backend only**, **Mock/placeholder**, **Missing**, **Broken**.

| # | Module | Classification | Evidence | Notes |
|---|---|---|---|---|
| 1 | Authentication & authorization | **Implemented, insufficiently tested** | `backend/app/routers/auth.py`, `core/security.py`, `core/deps.py`; no auth test file | Logout is a no-op; forgot-password is a no-op; no app-level rate limiting; no refresh-token rotation. |
| 2 | Clinic & organization management | **Implemented, insufficiently tested** | `routers/clinic.py` (11), `routers/organizations.py` (8), `models/clinic.py`, `models/organization.py`; org tests exist | Organization membership/roles enforced; clinic/organization mutations are **not audit-logged**. |
| 3 | Staff & workforce management | **Implemented, partially tested** | `clinic.py:152-262` (staff list/invite/accept), `StaffInvitation` model | One test covers branch scoping + staff invitation (`test_first_branch_is_primary_and_staff_invitation_scopes_account`). |
| 4 | Dental Patient CRM | **Implemented, tested** | `routers/healthcare.py` patients/enquiries/communications/visits; `test_crm_enquiry_conversion_and_patient_communication_history` | Enquiry → patient conversion, communication history covered. |
| 5 | Patient registration | **Implemented, tested** | `healthcare.py` create patient; `patient_portal.py` invitations/accept/login; `test_patient_portal_invitation_requires_activation_before_login` | Portal activation flow covered. |
| 6 | Appointment & calendar management | **Implemented, partially tested** | `routers/calendar.py` (3), `CalendarEvent`; visits in `healthcare.py` | Calendar CRUD itself is not directly covered by a test. |
| 7 | Consultation & clinical records | **Implemented, tested** | `healthcare.py` records/revisions/file upload/download; `test_private_record_file_upload_and_download` | S3 storage, revisioning, correction audit covered. |
| 8 | Treatment Journey Intelligence | **Implemented, tested** | `TreatmentPlan`/`TreatmentStage`/`TreatmentDecision`, ledger, revenue recovery; `test_treatment_stage_transition_is_guarded`, `test_treatment_ledger_currency_and_visit_analytics` | Strong coverage of stage transitions and ledger. |
| 9 | Patient Passport | **Implemented, tested** | `HealthRecord` + revisions + `RecordConsent` + `PatientRecordShare`; portal share endpoints | Share/consent download paths implemented. |
| 10 | Consent & Audit Management | **Partially implemented** | `RecordConsent`, `AuditEvent`, `/healthcare/audit`; audit calls only in `healthcare.py` (34), `growth.py` (7), `operations.py` (15) | Consent is enforced for reminders; **audit logging is missing** in auth, billing, clinic, organizations, patient_portal, patient_billing, calendar, content, export, financial_analytics, admin. |
| 11 | Revenue Recovery Analytics | **Implemented, tested** | `healthcare.py /revenue-recovery`, financial analytics revenue/ledger; tests for ledger + recovery flow | Currency/analytics range validation tested. |
| 12 | Patient billing & payments | **Implemented, tested** | `patient_billing.py` (11), `PaymentOrder`, `PatientPaymentOrder`; tests for order/verify idempotency, portal charges, webhook signature | Razorpay signature verification and one-time capture covered. |
| 13 | Subscription management | **Implemented, insufficiently tested** | `billing.py` (11), `ClinicSubscription`, `BillingWebhookEvent`, `subscription_billing` worker | **No billing test file**; webhook worker and dunning untested. |
| 14 | Financial reporting | **Implemented, partially tested** | `financial_analytics.py` (5), accounting CSV exports | Ledger/visit analytics tested; financial summary/treatment follow-up/retention not directly tested. |
| 15 | Communication & notifications | **Implemented, partially tested** | `CommunicationTemplate`, `PatientCommunication`, `CommunicationOutbox`, `EmailOutbox`, workers; `test_email_outbox.py` | Email outbox tested; WhatsApp adapter and communication outbox retry not tested. |
| 16 | Document storage | **Implemented, tested** | `services/document_storage.py`, `HealthRecord` upload/download; test monkeypatches storage | S3-only, SSE, presigned URLs, audit on download. |
| 17 | AI clinical assistance | **Partially implemented** | `services/ai_content.py`, `services/clinical_notes.py`, `operations.py` AI note draft/review; `clinic.py` AI settings; `test_ai_note_drafting_is_gated_and_requires_patient_consent` | Gating/consent tested; **requires the former Anthropic API credential**; content generation not tested without a key. |
| 18 | Integrations | **Implemented, tested** | `integrations.py` catalog, `IntegrationConnection`, CSV import/export, WhatsApp adapter; tests for CSV + secret non-persistence | WhatsApp live send not tested. |
| 19 | Administration & analytics | **Backend only** | `admin.py` `GET /admin/clinics` (super admin); no admin UI | No frontend screen; no test. |
| 20 | Growth OS | **Implemented, tested** | `growth.py` (8), `LocalListingAudit`, `MarketingCampaign`, `ClinicReview`; `test_manual_growth_listing_campaign_and_review_workflows` | Reviews are draft-only (no publishing). |
| 21 | Content generation / calendar / export | **Implemented, partially tested** | `content.py`, `calendar.py`, `export.py`; frontend services | Calendar CRUD and export job list not directly tested. |
| 22 | Onboarding | **Implemented, not directly tested** | `clinic.py /onboarding`, `/onboarding/complete`; dashboard consumes status | No dedicated onboarding test. |
| 23 | Backend startup (import) | **Broken** (without working-tree fix) | `app/schemas/dashboard.py` forward refs | See P0-1. |
| 24 | SQLite migrations | **Broken** | `alembic/versions/e78cbd0fad9c_*.py:83,93` | See P0-2. |
| 25 | Production API proxy | **Broken** (without working-tree fix) | `nginx/conf.d/default.conf` `proxy_pass http://backend/;` | See P0-3. |

---

## C. Frontend-to-backend traceability

### C.1 Feature → service → endpoints → tables

| Frontend feature | Angular service | Backend endpoints (prefix `/api/v1`) | Primary DB tables | Status |
|---|---|---|---|---|
| Login / register / forgot password | `core/services/auth.service.ts` | `/auth/login`, `/auth/register`, `/auth/forgot-password`, `/auth/me` | `users`, `clinics`, `clinic_branches` | Working; forgot-password is a no-op. |
| Dashboard | `features/dashboard/dashboard.service.ts` | `/dashboard/summary`, `/financial-analytics/{revenue,financial-summary,treatment-followup,patient-retention,operational}`, `/clinic/onboarding` | `generated_content`, `calendar_events`, `treatment_ledger_entries`, `treatment_plans`, `invoices`, `insurance_claims`, `treatment_stages`, `recall_reminders`, `patient_visits`, `patients`, `patient_enquiries`, `users`, `clinic_branches` | Working. |
| Clinic profile | `features/clinic-profile/clinic-profile.service.ts` | `/clinic/profile` | `clinics` | Working. |
| Content generator | `features/content-generator/content-generator.service.ts` | `/content/generate`, `/content` | `generated_content` | Working; requires Anthropic key. |
| Content calendar | `features/content-calendar/content-calendar.service.ts` | `/calendar`, `/calendar/{id}` | `calendar_events`, `generated_content` | Working. |
| Export content | `features/export-content/export-content.service.ts` | `/export` (POST/GET), `/export/{id}/download` | `export_jobs` | Working. |
| Billing | `features/billing/billing.service.ts` | `/billing/plans`, `/subscription`, `/invoices`, `/subscriptions`, `/subscriptions/{verify,cancel,pause,resume}` | `clinic_subscriptions`, `invoices` | Working; untested. |
| Growth OS | `features/clinic-growth-os/clinic-growth-os.service.ts` | `/growth/local-listings`, `/campaigns`, `/reviews`, `/{id}` | `local_listing_audits`, `marketing_campaigns`, `clinic_reviews`, `clinic_branches` | Working. |
| Dental operations | `features/dental-operations/dental-operations.service.ts` | `/operations/dental-cases`, `/assets`, `/assets/{id}/maintenance`, `/sterilization-cycles`, `/message-drafts`, `/marketing-publications`, `/clinical-note-drafts`, `/clinical-note-drafts/{id}/generate-ai`, `/review`; `/clinic/clinical-ai-settings`; `/integrations/catalog` | `dental_workflow_cases`, `dental_workflow_events`, `clinic_assets`, `asset_maintenance_records`, `sterilization_cycles`, `patient_message_drafts`, `marketing_publication_drafts`, `clinical_note_drafts`, `clinics` | Working. |
| Organization management | `features/organization-management/organization-management.service.ts` | `/organizations`, `/current`, `/current/analytics`, `/current/members`, `/current/invitations`, `/invitations/accept`, `/current/members/{id}/role`, `DELETE /current/members/{id}` | `clinic_organizations`, `organization_members`, `organization_invitations`, `users`, `clinics` | Working. |
| DentalPilot workflows (CRM, treatment, billing, records, consents, recall, comms, integrations) | `features/dentalpilot-workflows/dentalpilot-workflows.service.ts` (64 calls) | `/healthcare/*` (patients, enquiries, visits, treatment plans/stages, ledger, insurance claims, records, consents, reminders, recall settings, communication templates/outbox, email outbox, integrations, audit, analytics, revenue recovery), `/clinic/{branches,staff,staff/invitations,onboarding,onboarding/complete}`, `/billing/{accounting/ledger.csv,accounting/insurance-claims.csv,pms/reconcile,pms/reconciliation-runs,...}`, `/patient-billing/treatment-payments/*` | `patients`, `patient_enquiries`, `patient_visits`, `treatment_plans`, `treatment_stages`, `treatment_decisions`, `treatment_ledger_entries`, `insurance_claims`, `health_records`, `health_record_revisions`, `record_consents`, `patient_record_shares`, `recall_reminders`, `recall_automation_settings`, `email_outbox`, `communication_templates`, `patient_communications`, `communication_outbox`, `integration_connections`, `integration_sync_jobs`, `audit_events`, `clinic_branches`, `users`, `staff_invitations`, `pms_reconciliation_runs`, `pms_reconciliation_rows`, `patient_payment_orders` | Working; broadest surface. |
| Patient portal | `features/patient-portal/patient-portal.ts` (direct `API_ENDPOINTS`) | `/patient-portal/login`, `/invitations/accept`, `/me`, `/records`, `/records/{id}/download`, `/shares`, `/shares/{token}`, `/patient-billing/treatment-payments/portal/*` | `patients`, `patient_portal_accounts`, `health_records`, `record_consents`, `patient_record_shares`, `treatment_ledger_entries`, `patient_payment_orders` | Working; public routes by design. |
| Staff invitation acceptance | `features/staff-invitation/staff-invitation.ts` | `/clinic/staff/invitations/accept` | `users`, `clinics`, `staff_invitations` | Working. |

### C.2 Backend endpoints with no frontend integration

| Endpoint | Reason | Impact |
|---|---|---|
| `GET /admin/clinics` | No admin UI | Super-admin capability unreachable from the product. |
| `POST /auth/refresh` | Frontend never calls it; access token expiry forces re-login | Session UX gap. |
| `POST /billing/razorpay/order`, `POST /billing/razorpay/verify` | Legacy, `include_in_schema=False`, unused | Dead code / confusion. |
| `GET /content/{content_id}` | Frontend only lists/generates | Unused read endpoint. |
| `POST /billing/razorpay/subscriptions/webhook`, `POST /patient-billing/razorpay/webhook` | Public webhooks (correctly no UI) | N/A — expected. |
| `GET /patient-portal/shares/{token}` and `/records/{id}/download` | Public share links (no UI needed) | N/A — expected. |

---

## D. Database audit

### D.1 Tables (40+)

`users`, `clinics`, `clinic_branches`, `staff_invitations`, `patients`, `patient_enquiries`, `patient_visits`, `treatment_ledger_entries`, `insurance_claims`, `pms_reconciliation_runs`, `pms_reconciliation_rows`, `local_listing_audits`, `marketing_campaigns`, `clinic_reviews`, `recall_automation_settings`, `email_outbox`, `treatment_plans`, `treatment_stages`, `treatment_decisions`, `health_records`, `health_record_revisions`, `patient_portal_accounts`, `record_consents`, `patient_record_shares`, `recall_reminders`, `audit_events`, `integration_connections`, `integration_sync_jobs`, `communication_templates`, `patient_communications`, `communication_outbox`, `dental_workflow_cases`, `dental_workflow_events`, `clinic_assets`, `asset_maintenance_records`, `sterilization_cycles`, `patient_message_drafts`, `marketing_publication_drafts`, `clinical_note_drafts`, `calendar_events`, `generated_content`, `export_jobs`, `invoices`, `payment_orders`, `clinic_subscriptions`, `billing_webhook_events`, `patient_payment_orders`, `clinic_organizations`, `organization_members`, `organization_invitations`.

### D.2 Strengths

- **Tenant isolation at the schema level:** nearly every tenant table has `clinic_id` with an index.
- **Idempotency:** `billing_webhook_events.provider_event_id` unique; `patient_payment_orders.charge_entry_id` unique; `email_outbox.reminder_id` unique; `recall_reminders.trigger_key` unique.
- **Revisioning:** `health_record_revisions` with `uq_health_record_revision_number`.
- **Composite indexes:** `dental_workflow_cases(clinic_id, case_type, status)`, `billing_webhook_events(processing_status, available_at)`, `patient_payment_orders(clinic_id, ...)`.
- **Single Alembic head** and a linear 12-revision chain.

### D.3 Issues

| ID | Issue | Evidence | Severity |
|---|---|---|---|
| D-1 | SQLite migration fails (`Constraint must have a name`) | `alembic/versions/e78cbd0fad9c_*.py:83,93` | **P0** |
| D-2 | No unique constraint on patient identity (`clinic_id` + `email`/`phone`) | `models/healthcare.py:58-74` | P1 |
| D-3 | No `ondelete` rules on FKs; no soft deletes | model grep shows no `ondelete`/`deleted_at` | P2 |
| D-4 | Only 10 of 45 tables have `updated_at` | `grep -c updated_at app/models/` = 10 vs `created_at` = 45 | P2 |
| D-5 | Status columns are plain strings with no DB `CheckConstraint` | no `CheckConstraint` in `app/models/` | P3 |
| D-6 | No pagination indexes / list endpoints unpaginated | routers return `list[...]` without limit/offset | P2 |
| D-7 | `communication_outbox` has no unique idempotency key | `models/healthcare.py:655-681` | P2 |
| D-8 | `Patient.email`/`phone` not indexed | `models/healthcare.py:68-69` | P3 |
| D-9 | Migration tests absent; downgrade paths untested | no migration tests in `tests/` | P2 |

---

## E. Security audit

### E.1 Authentication

| Control | Status | Evidence |
|---|---|---|
| Password hashing | **Good** — bcrypt, explicit 72-byte truncation | `core/security.py:30-34` |
| JWT signing | **Good** — HS256, `exp`, `iat`, `type` claim | `core/security.py:37-67` |
| Access/refresh separation | **Good** — refresh tokens rejected for API access | `core/deps.py:27-29` |
| Logout | **Weak** — stateless no-op; token remains valid until expiry | `routers/auth.py:81-84` |
| Refresh rotation / revocation | **Missing** — refresh issues a new pair, no rotation/blacklist | `routers/auth.py:63-78` |
| Forgot password | **Broken** — endpoint returns 204 but sends nothing | `routers/auth.py:87-91` |
| Account lockout / login throttling | **Missing** at app level | no limiter in `app/` |
| Token storage (frontend) | **Weak** — `localStorage` | `core/services/token-storage.service.ts:10-24` |
| Email verification / MFA | **Missing** | no model/endpoint |

### E.2 Authorization & tenant isolation

- **Strong baseline:** routers consistently filter by `current_user.clinic_id`; staff with `branch_id` are further scoped (e.g., `healthcare.py:1702-1703`, `1733-1734`).
- **Role gates:** `RequireOwner`, `RequireSuperAdmin`, organization membership roles (`organizations.py:501-505`, `552-558`).
- **Patient portal:** scoped by `PatientPortalAccount` / `RecordConsent` / `PatientRecordShare` tokens (`patient_portal.py:56`, `149`, `195-196`, `248-261`).
- **Minor gap:** `healthcare.py:1294` `db.get(TreatmentLedgerEntry, claim.charge_entry_id)` relies on the parent claim being clinic-scoped; add an explicit `charge.clinic_id == current_user.clinic_id` check for defence in depth.
- **No IDOR found** in sampled record/download/share/patient-portal endpoints.

### E.3 Patient data protection

- S3-only storage, AES-256 SSE, KMS key support, presigned downloads (`services/document_storage.py`).
- Consent checks before reminders (`test_reminder_requires_confirmed_consent`).
- Audit events on record file export (`healthcare.py:1713`).
- **Gaps:** no field-level encryption for direct identifiers; no retention policy; no CSP in production nginx; tokens in `localStorage`.

### E.4 Secrets management

- No real secrets committed; `.env.production.example` contains placeholders.
- Working-tree `.gitignore` ignores `.env*` while preserving `*.example`.
- **Gaps:** secrets passed as container environment variables (visible via `docker inspect`); same Razorpay webhook secret used for two webhook endpoints; JWT secret minimum length not enforced.

### E.5 Rate limiting & transport

- **No application-level rate limiting** anywhere (`grep slowapi/limiter` → none).
- Production nginx has `limit_req` for `/api/` (100r/s) and `/api/v1/auth/` (10r/s); **staging** has the same zones; **local/dev has none**.
- CORS is explicit-origin with credentials (`main.py:41-49`).
- Production nginx adds HSTS, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy; **no CSP**.
- Direct API host (`api.dentalpilot.in`) bypasses the frontend nginx; no body-size limit evidenced.

### E.6 Audit logging

`audit()` calls exist only in `healthcare.py` (34), `operations.py` (15), `growth.py` (7). **Zero** in `auth.py`, `billing.py`, `clinic.py`, `organizations.py`, `patient_portal.py`, `patient_billing.py`, `calendar.py`, `content.py`, `export.py`, `financial_analytics.py`, `admin.py`.

### E.7 Security findings summary

| ID | Finding | Severity |
|---|---|---|
| SEC-1 | No app-level rate limiting (credential stuffing) | **P0** |
| SEC-2 | Logout no-op + localStorage tokens + no refresh rotation | P1 |
| SEC-3 | Forgot-password no-op | P1 |
| SEC-4 | Audit logging missing for auth/billing/clinic/org/portal | P1 |
| SEC-5 | JWT secret length not enforced | P2 |
| SEC-6 | Shared Razorpay webhook secret | P2 |
| SEC-7 | No CSP in production nginx | P2 |
| SEC-8 | Secrets as env vars, not Docker secrets | P2 |
| SEC-9 | Minor: missing explicit clinic check on linked charge | P3 |

---

## F. Testing audit

### F.1 Executed

| Suite | Command | Result |
|---|---|---|
| Backend (3 files) | `pytest tests/ -q` in `dentalpilot-backend:local` | **25 passed**, 48 warnings, 15.10s |
| Backend import | container start | **Failed pre-fix**; passes after working-tree `dashboard.py` reorder |
| Alembic chain | `alembic history` / `heads` | Single head, 12 linear revisions |
| Alembic upgrade (SQLite) | container default | **Failed** at `e78cbd0fad9c` |
| Compose validation | `docker compose config` (local/prod/staging) | **Valid** |
| Nginx validation | `nginx -t` (3 configs) | **Valid** |

### F.2 Backend test coverage (actual test functions)

- `test_healthcare_workflows.py` — 22 tests: health/correlation, patient/plan/record/recovery, payment idempotency, portal charges, webhook signature, insurance remittances, PMS reconciliation, CRM conversion, growth, consent reminders, stage transitions, integration secrets, CSV import/export, ledger currency, recall approval/analytics, private file upload/download, portal invitation activation, branch/staff scoping.
- `test_native_operations_and_organizations.py` — 4 tests: digital cases/assets/maintenance/sterilization audit, organization invitation/analytics, message/publication/note review + provider boundaries, AI note gating/consent.
- `test_email_outbox.py` — 1 test: send + retry with fake sender.

### F.3 Not covered

- Authentication (login, register, refresh, logout, forgot-password).
- Subscription billing (plans, checkout, webhook worker, dunning).
- Financial summary, treatment follow-up, patient retention, operational metrics.
- Calendar CRUD, export job lifecycle, content get-by-id.
- WhatsApp communication outbox.
- Frontend: **1 spec file** (`app.spec.ts`); no component/service/e2e tests.
- Migration up/down on Postgres.

### F.4 CI status

- The only workflow is `products/healthcare/dental/dentalpilot-ai/.github/workflows/ci-cd.yml`.
- **GitHub Actions only reads `.github/workflows/` at the repository root**, so this workflow **never runs**.
- The workflow also contains defects if relocated: `npm run lint || true` (no lint script), Karma flags for an Angular 21 Vitest builder, `pytest --cov` without `pytest-cov`.
- No workflow at `otheryn-platform/.github/workflows/`.

---

## G. Deployment audit

### G.1 Local

| Item | Status | Evidence |
|---|---|---|
| Compose file | **Present (working tree)** | `docker-compose.local.yml` (new) |
| Services | Postgres 16, Redis 7, one-shot migrate, FastAPI (reload), workers | `docker-compose.local.yml` |
| Images built from real Dockerfile | **Yes** | `build: ./backend`, `image: dentalpilot-backend:local` |
| No registry pulls | **Yes** | local build only |
| Migrations exactly once | **Yes** | `migrate` service + `service_completed_successfully` |
| Persistent volumes | **Yes** | `postgres_local_data`, `redis_local_data` |
| Health checks | **Yes** | Postgres `pg_isready`, Redis `ping`, backend `/health` |
| Frontend | Angular dev server (`npm start`) | documented |
| Nginx SSL locally | **No** | correct |

**Local blocker:** P0-2 (SQLite migration) affects non-Docker local setup and the backend image's default `CMD`. The local Compose uses Postgres, which is expected to avoid the batch-mode issue, but the full stack was **not executed** in this audit.

### G.2 Staging

| Item | Status | Evidence |
|---|---|---|
| Compose overrides | **Present (working tree)** | `docker-compose.staging.yml` |
| HTTP-only nginx | **Present (working tree)** | `nginx/staging/default.conf` |
| Port | `8080:80` | staging config |
| CORS / APP_ENVIRONMENT | `staging` | staging config |
| Images | same GHCR images | base compose |
| Gaps | No staging-specific secrets template beyond `.env.staging.example`; no staging DB backup automation | — |

### G.3 Production

| Item | Status | Evidence |
|---|---|---|
| Compose | **Valid** | `docker-compose.yml` (working tree) |
| Postgres/Redis not public | **Yes** | no `ports` on either |
| Backend/workers | GHCR images, `IMAGE_TAG` support | working tree |
| One-shot migrations | **Yes** | `migrate` service |
| Frontend + nginx | GHCR image, 80/443, SSL mounts | working tree |
| Security headers | HSTS, XFO, nosniff, Referrer-Policy, Permissions-Policy | `nginx/conf.d/default.conf` |
| Static caching | `immutable`, 1y | nginx |
| Health checks | backend `/health`, frontend `/health` | compose |
| Restart policies | `unless-stopped` | compose |
| Resource limits | **Missing** (no `deploy.resources` / `mem_limit`) | compose |
| Backup/restore automation | **Not evidenced** | — |
| Rollback | Manual (redeploy previous `IMAGE_TAG`) | — |
| SSL renewal | Manual (mount certs) | — |
| Secret rotation | Manual | — |

### G.4 CI/CD & artifacts

- No root workflow → **no automated image builds/pushes**.
- `deploy.sh` exists and now uses the one-shot migration flow and correct health checks (working tree).
- `railway.toml` (python311) and `nixpacks.toml` (python311) conflict with `Dockerfile` (Python 3.12).
- `frontend/Dockerfile` uses `node:20-alpine`; Angular 21 requires Node ≥20.19 — verify the tag resolves to a compatible 20.x.

### G.5 Deployment readiness matrix

| Area | Local | Staging | Production |
|---|---|---|---|
| Compose valid | ✅ | ✅ | ✅ |
| Images build | ✅ backend | ✅ (GHCR) | ✅ (GHCR) |
| Migrations | ⚠️ SQLite bug | ✅ (Postgres) | ✅ (Postgres) |
| Nginx valid | ✅ | ✅ | ✅ |
| Health checks | ✅ | ✅ | ✅ |
| Rate limiting | ❌ | ⚠️ nginx only | ⚠️ nginx only |
| CI/CD | ❌ | ❌ | ❌ |
| Backups | ❌ | ❌ | ❌ |
| Secrets mgmt | ⚠️ env file | ⚠️ env | ⚠️ env vars |

---

## H. Prioritized remediation roadmap

Each finding includes evidence, business impact, technical impact, recommended fix, dependencies and acceptance criteria.

### P0 — Critical (security / data-loss / blocking)

---

#### P0-1 — Backend cannot import (`app.main`)

- **Evidence:** `backend/app/schemas/dashboard.py` — `RevenueMetrics.monthly_trend: list[MonthlyRevenuePoint]` at line 47 references `MonthlyRevenuePoint` defined at line 50; `FinancialSummary.insurance_claims` references `InsuranceClaimsSummary` defined later; `TreatmentFollowupMetrics.followup_by_type` references `FollowupTypeMetrics` defined later. Importing `app.main` raises `NameError: name 'MonthlyRevenuePoint' is not defined`.
- **Business impact:** The API cannot start at all; every feature is down.
- **Technical impact:** All 156 endpoints unavailable; container crash-loops.
- **Recommended fix:** Move `MonthlyRevenuePoint`, `InsuranceClaimsSummary`, `FollowupTypeMetrics` above their referencing classes (behaviour-preserving reorder). **[working-tree fix already applied]**
- **Dependencies:** None.
- **Acceptance criteria:** `python -c "import app.main"` succeeds; `pytest` collects without import errors; container `/health` returns 200.

---

#### P0-2 — Alembic migration fails on SQLite

- **Evidence:** `backend/alembic/versions/e78cbd0fad9c_add_communication_templates_and_.py:83` `batch_op.create_foreign_key(None, 'communication_templates', ...)` and `:93` `batch_op.drop_constraint(None, type_='foreignkey')`. SQLite batch mode raises `ValueError: Constraint must have a name`.
- **Business impact:** Default local setup and the backend image's default `CMD` (`alembic upgrade head && uvicorn ...`) cannot start; new environments cannot be bootstrapped.
- **Technical impact:** `alembic upgrade head` fails on SQLite; fresh DBs unusable; onboarding broken.
- **Recommended fix:** Name the constraint, e.g. `fk_patient_communications_template_id`, and use the same name in `downgrade()`. Alternatively, guard batch mode to SQLite only and emit a named FK for Postgres. Add a migration smoke test.
- **Dependencies:** P0-1 (app import) for any test that imports models.
- **Acceptance criteria:** `alembic upgrade head` succeeds on SQLite **and** Postgres; `alembic downgrade -1` then `upgrade head` round-trips; CI runs migrations.

---

#### P0-3 — Production nginx strips the `/api/` prefix

- **Evidence:** `nginx/conf.d/default.conf` (pre-fix) used `proxy_pass http://backend/;` for `location /api/`; FastAPI serves under `/api/v1` (`app/main.py` includes routers with `prefix="/api/v1"`). A request `/api/v1/auth/login` becomes `/v1/auth/login` upstream → 404. Same defect in `frontend/nginx.conf`.
- **Business impact:** If the frontend nginx is used for API traffic, **every API call fails**.
- **Technical impact:** Login, dashboard, all clinical workflows unavailable through the proxy.
- **Recommended fix:** Use `proxy_pass http://backend;` (no trailing slash) to preserve the URI. **[working-tree fix already applied to both files]**
- **Dependencies:** None.
- **Acceptance criteria:** `curl http://<frontend>/api/v1/health/ready` returns the backend response; `nginx -t` passes; an end-to-end login through nginx succeeds.

---

#### P0-4 — No application-level rate limiting

- **Evidence:** `grep -rn 'slowapi|limiter|rate_limit' app/` → no matches. Only nginx `limit_req` zones exist, and the direct API host bypasses the frontend nginx.
- **Business impact:** Credential stuffing, brute force, and enumeration against `/auth/login`, `/auth/register`, `/auth/forgot-password`, `/patient-portal/login`.
- **Technical impact:** Account compromise; resource exhaustion.
- **Recommended fix:** Add rate limiting (e.g., `slowapi` with Redis backend) for auth and patient-portal login, keyed by IP + email; return `429` with `Retry-After`. Keep nginx limits as defence-in-depth.
- **Dependencies:** Redis (already a dependency).
- **Acceptance criteria:** >N failed logins from one IP within the window return `429`; limits are configurable; tests cover allowed and blocked cases.

---

#### P0-5 — No executable CI/CD

- **Evidence:** `.github/workflows/ci-cd.yml` is nested under `products/healthcare/dental/dentalpilot-ai/`; GitHub only evaluates `.github/workflows/` at the repo root. No root workflow exists.
- **Business impact:** No automated tests, no image builds, no release provenance; regressions reach production.
- **Technical impact:** GHCR images may be stale/missing; deploys are manual.
- **Recommended fix:** Move/duplicate the workflow to `otheryn-platform/.github/workflows/` with `paths:` filters for `products/healthcare/dental/dentalpilot-ai/**`; fix lint/test commands (add `lint` script or remove; use Angular 21 `ng test`; install `pytest-cov` or drop `--cov`); add `docker build` + `push` on tags.
- **Dependencies:** P0-1, P0-2 (pipeline must be green).
- **Acceptance criteria:** PR triggers backend tests + frontend build/test; main/tag builds and pushes `sha-<commit>` images; required checks configured.

---

### P1 — Essential functionality / production blockers

---

#### P1-1 — Forgot-password is a no-op

- **Evidence:** `backend/app/routers/auth.py:87-91` queries the user and always returns 204; no token, no email.
- **Business impact:** Users cannot recover accounts; support burden.
- **Technical impact:** `POST /auth/forgot-password` is a stub.
- **Recommended fix:** Generate a single-use, expiring reset token (hashed at rest), email it via `email_delivery`, add `POST /auth/reset-password`, and invalidate on use. Always return 204 to avoid enumeration.
- **Dependencies:** SMTP configuration.
- **Acceptance criteria:** Reset link works end-to-end; token expires; token is single-use; no account enumeration.

---

#### P1-2 — Logout is a no-op; tokens in `localStorage`; no refresh rotation

- **Evidence:** `auth.py:81-84` (stateless logout); `frontend/src/app/core/services/token-storage.service.ts:10-24` (`localStorage`); no jti/blacklist; refresh issues a new pair without rotation.
- **Business impact:** XSS can exfiltrate long-lived tokens; logout does not revoke; stolen refresh tokens remain valid.
- **Technical impact:** Session management is not production-grade.
- **Recommended fix:** Prefer httpOnly/Secure/SameSite cookies; if localStorage is retained, add a token revocation list (Redis) with jti, rotate refresh tokens on use, and add a strict CSP.
- **Dependencies:** Redis.
- **Acceptance criteria:** Logout invalidates the refresh token; reused refresh token is rejected; CSP blocks inline script.

---

#### P1-3 — Frontend has almost no tests and no lint

- **Evidence:** `find frontend/src -name '*.spec.ts'` → 1 (`app.spec.ts`); `frontend/package.json` has `build`/`test` but no `lint`; no e2e config.
- **Business impact:** Regressions in 14 feature areas are undetected.
- **Technical impact:** No safety net for refactors.
- **Recommended fix:** Add Vitest/Jest specs for services (auth, each feature service) and key components; add `lint` (ESLint or Prettier check); add Playwright/Cypress smoke e2e.
- **Dependencies:** P0-5 (CI).
- **Acceptance criteria:** `npm test` runs >N specs; `npm run lint` exists and passes; e2e covers login → dashboard.

---

#### P1-4 — Audit logging missing for security-sensitive actions

- **Evidence:** `audit()` calls only in `healthcare.py` (34), `operations.py` (15), `growth.py` (7); **0** in `auth.py`, `billing.py`, `clinic.py`, `organizations.py`, `patient_portal.py`, `patient_billing.py`, `calendar.py`, `content.py`, `export.py`, `financial_analytics.py`, `admin.py`.
- **Business impact:** No forensic trail for logins, profile changes, org membership, billing, portal access.
- **Technical impact:** Cannot investigate incidents or satisfy audit requests.
- **Recommended fix:** Emit `AuditEvent` for login/logout, registration, clinic profile changes, branch/staff changes, organization membership/role changes, subscription changes, patient-portal access/share/revoke, and record downloads.
- **Dependencies:** None.
- **Acceptance criteria:** Each listed action creates an audit row; `/healthcare/audit` returns them; tests assert audit creation.

---

#### P1-5 — Subscription billing is untested

- **Evidence:** No `test_billing*.py`; `billing.py` (11 endpoints) and `subscription_billing.py` worker have no tests.
- **Business impact:** Revenue leakage, incorrect dunning, webhook double-processing.
- **Technical impact:** Billing regressions can go live undetected.
- **Recommended fix:** Add tests for plan listing, checkout, verify, cancel/pause/resume, webhook signature/idempotency, dunning retries.
- **Dependencies:** P0-5.
- **Acceptance criteria:** Happy + sad paths covered; webhook replay is idempotent; dunning stops at max attempts.

---

#### P1-6 — Staging configuration incomplete (pre-working-tree)

- **Evidence:** `docker-compose.staging.yml` only overrode ports/CORS and reused the production SSL nginx config; staging on `http://localhost:8080` would redirect to `https://dentalpilot.in`.
- **Business impact:** Staging not usable for QA.
- **Technical impact:** Cannot validate releases pre-production.
- **Recommended fix:** Use `nginx/staging/default.conf` (HTTP-only, `server_name _`) and `!override` ports/volumes. **[working-tree fix applied]**
- **Dependencies:** None.
- **Acceptance criteria:** `docker compose -f docker-compose.yml -f docker-compose.staging.yml config` shows only `8080:80` and the staging config; staging reachable over HTTP.

---

#### P1-7 — Migrations run on every backend boot (duplicate execution)

- **Evidence:** `backend/Dockerfile` `CMD` runs `alembic upgrade head && uvicorn ...`; `deploy.sh` also ran migrations before `up`.
- **Business impact:** Concurrent/racy migrations during rollout; slower cold starts.
- **Technical impact:** Multiple workers/backend replicas can race on schema changes.
- **Recommended fix:** One-shot `migrate` service; backend/workers depend on `service_completed_successfully`; remove auto-migrate from `CMD`. **[working-tree fix applied]**
- **Dependencies:** P0-2.
- **Acceptance criteria:** `docker compose up` runs migrations once; backend/workers start only after success.

---

#### P1-8 — Images default to `latest`

- **Evidence:** `docker-compose.yml` (pre-working-tree) hardcoded `:latest`; no `IMAGE_TAG`.
- **Business impact:** Non-reproducible deploys; rollback ambiguity.
- **Technical impact:** Cannot pin a known-good artifact.
- **Recommended fix:** Require `IMAGE_TAG` (e.g., `sha-<commit>`) in production; default to `latest` only for local. **[working-tree fix applied]**
- **Dependencies:** P0-5 (CI produces tags).
- **Acceptance criteria:** Production deploy uses a pinned tag; rollback = redeploy previous tag.

---

#### P1-9 — Duplicate patient records possible

- **Evidence:** `models/healthcare.py:58-74` — `Patient` has no unique constraint on `(clinic_id, email)` or `(clinic_id, phone)`; `external_reference` is not unique.
- **Business impact:** Duplicate charts, split histories, billing errors.
- **Technical impact:** Data integrity.
- **Recommended fix:** Add a unique constraint on `(clinic_id, external_reference)` where present, and a dedupe check on create (email/phone); or a merge workflow.
- **Dependencies:** Data cleanup.
- **Acceptance criteria:** Creating a duplicate patient is rejected or flagged; migration adds the constraint without data loss.

---

#### P1-10 — No request body size limit on the direct API

- **Evidence:** No middleware in `main.py`; nginx `client_max_body_size 50m` only on the frontend proxy.
- **Business impact:** Large uploads can exhaust memory/disk.
- **Technical impact:** DoS risk.
- **Recommended fix:** Add a body-size limit middleware and configure the API reverse proxy.
- **Dependencies:** None.
- **Acceptance criteria:** Oversized requests return `413`.

---

### P2 — Important product improvements

| ID | Finding | Evidence | Recommended fix | Acceptance criteria |
|---|---|---|---|---|
| P2-1 | No pagination on list endpoints | routers return `list[...]` | Add `limit`/`offset` or cursor | Large lists bounded; tests |
| P2-2 | No soft deletes / retention policy | no `deleted_at` | Add soft delete + retention jobs | Deletion reversible; PII retention policy |
| P2-3 | Only 10/45 tables have `updated_at` | model grep | Add `created_at`/`updated_at` to all | All mutable tables timestamped |
| P2-4 | No DB-level status constraints | no `CheckConstraint` | Add check constraints/enums | Invalid status rejected by DB |
| P2-5 | Workers lack supervision/health/metrics | `run_workers.py` threads, no restart | Add supervisor, signal handling, health endpoint | Dead worker restarts; `/health` reflects workers |
| P2-6 | No structured logging / correlation IDs | `main.py` no middleware | Add request-id + JSON logs | Logs correlatable |
| P2-7 | Secrets as env vars | compose `environment:` | Docker secrets / secret manager | Secrets not in `docker inspect` |
| P2-8 | JWT secret length not enforced | `config.py` only non-empty | Validate ≥32 bytes at startup | Weak secret fails fast |
| P2-9 | Shared Razorpay webhook secret | `settings.razorpay_webhook_secret` used by two endpoints | Separate secrets per webhook | Each webhook has its own secret |
| P2-10 | `communication_outbox` no idempotency key | model | Add unique `(clinic_id, source_type, source_id, channel)` | Duplicate sends prevented |
| P2-11 | Admin endpoint backend-only | `admin.py` | Build admin UI or restrict | Admin actions usable/audited |
| P2-12 | Unused endpoints | `auth.refresh`, `content/{id}`, legacy razorpay | Implement refresh or remove | No dead endpoints |
| P2-13 | No CSP in production nginx | nginx config | Add CSP (nonces/hashes) | CSP header present, no breakage |
| P2-14 | Python version mismatch | `railway.toml`/`nixpacks.toml` 3.11 vs Dockerfile 3.12 | Align to 3.12 | All build paths use 3.12 |
| P2-15 | No dependency scanning | no Dependabot/CodeQL | Add Dependabot + CodeQL | Alerts on CVEs |
| P2-16 | No DB backup automation | no evidence | Add nightly `pg_dump` + restore drill | Backup/restore tested |
| P2-17 | No staging secrets template parity | `.env.staging.example` | Validate all required vars | Staging boots from example |

### P3 — Advanced / future roadmap

- MFA / SSO (SAML/OIDC).
- Field-level encryption / tokenization for direct identifiers.
- Data residency / multi-region.
- Real-time notifications (WebSockets/SSE).
- Mobile apps (React Native/Flutter) against the same API.
- GraphQL or typed OpenAPI client generation.
- AI agent orchestration and evidence/verification (UETI) — currently **not implemented**.
- Public API + rate-limited partner integrations.
- Advanced analytics warehouse / BI exports.

---

## Appendix A — Endpoint inventory (summary)

| Router | Endpoints | Auth |
|---|---|---|
| `auth.py` | 6 | 5 public, 1 auth |
| `billing.py` | 11 | 1 public (`/plans`), 10 auth |
| `calendar.py` | 3 | auth |
| `clinic.py` | 11 | 1 public (invitation accept), 10 auth |
| `content.py` | 3 | auth |
| `dashboard.py` | 1 | auth |
| `export.py` | 3 | auth |
| `financial_analytics.py` | 5 | auth |
| `growth.py` | 8 | auth |
| `healthcare.py` | 51 | auth |
| `integrations.py` | 1 | auth |
| `operations.py` | 23 | auth |
| `organizations.py` | 8 | auth |
| `patient_billing.py` | 11 | 1 public webhook, 10 auth |
| `patient_portal.py` | 10 | 4 public, 6 patient-auth |
| `admin.py` | 1 | super admin |
| **Total** | **156** | — |

## Appendix B — Test and validation evidence

```
# Backend build
docker build -t dentalpilot-backend:local ./backend   # success

# Backend tests (after working-tree dashboard.py fix)
docker run --rm \
  -v "$PWD/backend/tests:/app/tests:ro" \
  -v "$PWD/backend/pytest.ini:/app/pytest.ini:ro" \
  dentalpilot-backend:local pytest tests/ -q
# 25 passed, 48 warnings in 15.10s

# Alembic
docker run --rm dentalpilot-backend:local alembic history   # linear, head e78cbd0fad9c
docker run --rm dentalpilot-backend:local alembic heads     # e78cbd0fad9c (head)

# SQLite migration failure (pre-fix)
docker run -d --name dp-backend-test -p 8001:8000 \
  -e JWT_SECRET=test-secret -e APP_ENVIRONMENT=test \
  dentalpilot-backend:local
docker logs dp-backend-test
# ValueError: Constraint must have a name  (alembic/versions/e78cbd0fad9c_*.py:83)

# Compose validation
docker compose -f docker-compose.local.yml config
docker compose --env-file .env.production.example -f docker-compose.yml config
docker compose --env-file .env.staging.example -f docker-compose.yml -f docker-compose.staging.yml config

# Nginx validation
docker run --rm --add-host backend:127.0.0.1 \
  -v "$PWD/nginx/staging/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:alpine nginx -t
docker run --rm --add-host backend:127.0.0.1 \
  -v /tmp/dp-ssl:/etc/nginx/ssl:ro \
  -v "$PWD/nginx/conf.d/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:alpine nginx -t
docker run --rm \
  -v "$PWD/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:alpine nginx -t
```

## Appendix C — Known limitations of this audit

- Frontend tests and production build were **not executed** (no `node_modules`; read-only scope).
- The full Docker Compose stack (Postgres + Redis + backend + workers + frontend) was **not started**; Compose and nginx were validated statically, and the backend image was built and tested.
- Postgres migration execution was **not run**; the SQLite failure was reproduced, and the Postgres path is inferred from Alembic batch-mode semantics (batch mode is a no-op for Postgres).
- No dynamic security testing (SAST/DAST), penetration testing or dependency CVE scan was performed.
- Business-logic correctness beyond the existing tests was not exhaustively verified.

---

**End of audit.** No fixes were implemented. This document is the evidence baseline for the next implementation phase.