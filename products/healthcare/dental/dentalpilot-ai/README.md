# DentalPilot AI

**DentalPilot AI is the first specialty product in the broader healthcare intelligence and infrastructure ecosystem described in the strategic blueprint. The parent-company name remains open.**

An AI-powered SaaS platform that helps dental clinics automate marketing — social media posts, patient education content, Google Business updates, and promotional campaigns — in minutes instead of hours.

## The problem

Dentists are excellent clinicians but often lack the time, ideas, or budget for consistent marketing. DentalPilot AI turns that into a few guided steps: describe a topic or treatment, and get ready-to-use, dental-specific content — unlike generic AI writing tools, it's built only around dental clinics, treatments, patient education, and local marketing.

## Product scope (MVP)

| Module | What it does | Status |
|---|---|---|
| Authentication | Sign up, log in, password reset | Real — JWT + bcrypt |
| Clinic Profile | Clinic details that steer all AI content (specialty, tone, audience) | Real |
| AI Content Generator | Generate platform-specific marketing posts from a topic/treatment | Real Claude API call (needs `ANTHROPIC_API_KEY`) |
| Content Calendar | Schedule generated content to go live | Real |
| Export Content | Bundle content as PDF/PNG/CSV | Real — CSV, PDF, PNG, and multi-image ZIP rendering |
| Subscription & Billing | Free/Starter/Professional/Enterprise plans, invoices | Real — Razorpay Standard Checkout (order creation + signature-verified capture) |
| Dashboard | Clinic's content/scheduling/usage at a glance | Real — live aggregation queries |
| Healthcare Workflows | Treatment lifecycle, revenue recovery, patient portal, consent/provenance, reminders, audit, clinic operations, analytics, and CSV exchange | MVP workflows — persisted API and Angular screens |

## Release 1.2.0

Version 1.2.0 completes the core dental workflow MVP with:

- Multi-branch operations, branch-scoped staff access, and clinic-issued staff invitations
- Guided onboarding status and branch/team management
- Treatment decisions with reasons, appointment scheduling, and decision history
- A native clinic-entered treatment ledger for charges, payments, and refunds, with collected
  totals and outstanding balances distinct from estimated treatment revenue
- Patient visits and date-filtered clinic analytics for workflow completion, follow-ups, patient
  retention, no-shows, and enquiry activity
- Record provenance fingerprints, version corrections, and correction history
- Private S3-compatible patient document uploads/downloads with clinic/branch authorization and
  server-side encryption when storage is configured
- Consent scope, recipient, expiry, revocation, patient portal downloads, and expiring share links
- Automated recall triggers with configurable intervals, staff approval, email-consent confirmation,
  and a retryable SMTP outbox worker
- Dental CRM enquiry conversion, communication history, and consent-confirmed email queuing
- Patient-portal self-service Razorpay checkout for a patient's own outstanding treatment charges
- Native digital dentistry case coordination, manual equipment/maintenance and sterilisation logs,
  patient communication drafts, marketing publication workflow, and clinician-entered note review
- Optional clinic groups with aggregate operational and financial reporting, separate totals per
  clinic currency, and owner/admin/reporting-only roles; standalone clinics remain supported
- Manual Local SEO audits, campaign planning, and review-response drafts
- Provider-neutral CSV import/export, configurable field mapping, and sync-job history
- Audit events for sensitive data access, modifications, and exchange
- Existing billing tiers, AI-credit usage, invoices, and content features

### Release boundaries

The 1.2.0 release does not claim medical-device approval, legal/compliance certification, or live
provider/device interoperability beyond configured Razorpay, S3-compatible storage, and SMTP paths.
PMS exchange remains CSV-only; digital dentistry cases, equipment, sterilisation, patient messages,
and marketing publications are manual workflows. Staff, patient and organization invitations still
require secure manual delivery. See [`RELEASE_NOTES.md`](RELEASE_NOTES.md) for implemented scope and
remaining boundaries.

### Planned after 1.2.0

- Vendor-specific PMS, DICOM imaging, scanner/lab, equipment and communication connectors
- Live marketing/review integrations and campaign attribution
- SMS/WhatsApp delivery, automated email for invitations/password resets, and session revocation
- DICOM viewers and device-level imaging workflows, validated clinical AI, equipment/IoT telemetry,
  and robotics interoperability
- Production credential management, monitoring, backup/recovery, and incident-response operations
- Referral and connected-care workflows
- Formal regulatory, privacy, clinical-governance, monitoring, and independent security reviews

Business model: subscription SaaS (Free / Starter / Professional / Enterprise), billed monthly or annually.

## Current state of this repo

- **`frontend/`** — a working Angular 21 app covering the MVP modules and healthcare workflows above.
- **`backend/`** — a working FastAPI app implementing the full REST contract the frontend expects. Run both together and the app works end-to-end: register, log in, edit your clinic profile, generate AI content, schedule it, and see it on the dashboard — all against a real database.

The 1.2.0 workflow release is an MVP, not production certification. Cloud storage and email require
operator-managed provider setup; live vendor integrations, advanced clinical/digital dentistry,
session revocation, and regulatory/compliance validation remain follow-up work — see
[`RELEASE_NOTES.md`](RELEASE_NOTES.md) and [`backend/README.md`](backend/README.md).

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Angular 21 (standalone, zoneless, signals) + Tailwind CSS v4 |
| Backend | FastAPI (Python), SQLAlchemy 2.0 + Alembic |
| Database | SQLite by default, swappable to PostgreSQL via one env var |
| AI | Claude (Anthropic API), structured outputs |
| Payments | Razorpay (Standard Checkout) |
| Cloud / Storage | Not yet wired up |

## Getting started

### 1. Start the backend and initialize the local database

Run these commands from the project root in Terminal 1:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python scripts/seed_hierarchy.py
uvicorn app.main:app --reload --port 8000
```

The migration creates/updates the local SQLite database at `backend/dentalpilot.db`.
The seed command creates a demo clinic and three demo users. Log in at
[`http://localhost:4200/auth/login`](http://localhost:4200/auth/login) using one of these:

| Role | Email | Password |
|---|---|---|
| Super Admin | `super-admin@dentalpilot.ai` | `password123` |
| Clinic Owner | `owner@brightsmiledental.io` | `password123` |
| Clinic Staff | `staff@brightsmiledental.io` | `password123` |

These are local demo credentials only. Do not use them in a public or production environment.

### 2. Start the frontend

Open Terminal 2 from the project root:

```bash
cd frontend
npm install
npm start
```

Open `http://localhost:4200`.

### 3. View the database in VS Code

The project uses SQLite locally, so you do not need to install or start a separate database
server. First run the backend migration above so `backend/dentalpilot.db` exists. Then:

1. In VS Code, open **Extensions** and install a SQLite database viewer/manager, such as
   **SQLite** by alexcvzz.
2. Open the Command Palette (`Cmd+Shift+P` on macOS), run **SQLite: Open Database**, and select
   `backend/dentalpilot.db`.
3. Use the extension's database explorer to browse tables such as `clinics`, `users`,
   `patients`, `treatment_plans`, `treatment_stages`, `health_records`, and `record_consents`.
4. If you seed data while the database view is open, refresh/reopen the database connection.

Use the application/API for normal data changes. Avoid editing production databases directly.
To connect PostgreSQL instead of local SQLite, see the database configuration in
[`backend/README.md`](backend/README.md).

See [`frontend/README.md`](frontend/README.md) and [`backend/README.md`](backend/README.md) for full setup, architecture, and configuration details.

## Repo layout

```
DentalPilot-AI/
  frontend/   Angular app — see frontend/README.md
  backend/    FastAPI app — see backend/README.md
```

## Roadmap

1. 1.2: secure document storage, identity verification, password reset, JWT revocation, secrets and backups.
2. 1.3: live PMS, imaging, laboratory, messaging, recurring billing and integration monitoring.
4. 2.0: referrals, connected care, multi-clinic operations and validated specialty expansion.
