# Contributing

> **Consolidated.** Contribution standards live in the authoritative documentation:

- Engineering/architecture standards: [`docs/notion/TECHNICAL_ARCHITECTURE.md`](docs/notion/TECHNICAL_ARCHITECTURE.md)
- Local development workflow: [`docs/notion/SETUP_AND_DEPLOYMENT.md`](docs/notion/SETUP_AND_DEPLOYMENT.md)

## Quick start

```bash
# Frontend
cd products/healthcare/dental/dentalpilot-ai/frontend && npm ci && npm start

# Backend
cd products/healthcare/dental/dentalpilot-ai/backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --reload-dir app --port 8000
```

## Conventions (recommended)

- Conventional Commits (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`).
- Feature branches; PR with tests and review.
- Migrations: one logical change, reviewed, tested up/down.
- No secrets or real patient data in commits.
- Preserve tenant isolation (`clinic_id`/`branch_id`) and audit sensitive actions.

See [`docs/notion/TECHNICAL_ARCHITECTURE.md`](docs/notion/TECHNICAL_ARCHITECTURE.md) for architecture and coding standards.