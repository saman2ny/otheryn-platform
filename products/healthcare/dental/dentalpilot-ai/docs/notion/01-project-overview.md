# DentalPilot AI — Project Overview

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
| Export Content | Bundle content as PDF/PNG/CSV | Job records real; file rendering not implemented |
| Subscription & Billing | Free/Starter/Professional/Enterprise plans, invoices | Real — Razorpay Standard Checkout (order creation + signature-verified capture) |
| Dashboard | Clinic's content/scheduling/usage at a glance | Real — live aggregation queries |

Business model: subscription SaaS (Free / Starter / Professional / Enterprise), billed monthly or annually.

## Current state of this repo

- **`frontend/`** — a working Angular 21 app covering all seven MVP modules above.
- **`backend/`** — a working FastAPI app implementing the full REST contract the frontend expects. Run both together and the app works end-to-end: register, log in, edit your clinic profile, generate AI content, schedule it, and see it on the dashboard — all against a real database.

What's not real yet: actual file generation for exports (PDF/PNG/CSV), plus a handful of production-readiness gaps (test suite, deployment, email sending). See the Backend doc for the exact list.

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

**Backend — http://localhost:8000**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set ANTHROPIC_API_KEY and RAZORPAY_KEY_ID/SECRET to enable those features
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend — http://localhost:4200** (in a second terminal)
```bash
cd frontend
npm install
npm start
```

See the Frontend and Backend docs for full setup, architecture, and configuration details.

## Repo layout

```
DentalPilot-AI/
  frontend/   Angular app
  backend/    FastAPI app
```

## Roadmap

1. Real file generation for exports (PDF/PNG/CSV).
2. Automated tests (backend pytest suite, frontend e2e), CI, deployment to AWS with managed Postgres.
3. Complete the Razorpay production rollout — create the configured monthly/annual plans, register the signed subscription webhook, and run the subscription-billing worker as a separate process.
4. Longer term: review management, appointment reminders, patient communication, analytics, and multi-clinic support.
