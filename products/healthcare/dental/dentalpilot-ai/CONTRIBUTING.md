# DentalPilot AI — Contributing

This guide describes how to contribute to DentalPilot AI. It covers workflow, coding conventions, migrations, tests, reviews and security.

> **Note on policy:** no existing team policy file was found in this repository. The branch-naming, commit-message and versioning conventions below are **recommended proposals**, not established rules. Follow any overriding team policy if one exists.

---

## 1. Prerequisites

- **Node.js** 22 LTS (20.19+ minimum) and **npm 11** — frontend.
- **Python 3.12** — backend.
- **Docker** with Compose v2 — local Postgres stack.
- **Git** and access to the repository.

Read first:

- [`README.md`](README.md) — architecture and quick start.
- [`ENVIRONMENT_GUIDE.md`](ENVIRONMENT_GUIDE.md) — local vs production.
- [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md).

---

## 2. Branch naming (recommended)

Use a type prefix and a short, hyphenated description:

```
feat/dentalpilot-<area>-<short-desc>
fix/dentalpilot-<area>-<short-desc>
chore/<short-desc>
docs/<short-desc>
refactor/<short-desc>
test/<short-desc>
ci/<short-desc>
```

Examples:

```
feat/dentalpilot-treatment-ledger-csv
fix/dentalpilot-portal-share-expiry
docs/dentalpilot-railway-guide
```

- Keep branch names lowercase.
- Include the ticket ID if one exists.
- Delete branches after merge.

---

## 3. Commit conventions (recommended)

Use **Conventional Commits**:

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

Scopes: `frontend`, `backend`, `db`, `api`, `auth`, `billing`, `workers`, `docker`, `ci`, `docs`.

Examples:

```
feat(backend): add treatment ledger CSV export
fix(frontend): handle expired patient share links
chore(db): add index on patient_enquiries clinic_id
```

- Imperative mood: "add", not "added".
- Reference issues in the footer: `Refs: DP-123`.
- Do not commit secrets, `.env` files, or generated build output.

---

## 4. Feature development workflow

1. **Create a branch** from `main`.
2. **Set up locally** (see §7/§8).
3. **Implement** the smallest change that satisfies the requirement.
4. **Add/update tests**.
5. **Run the checks** (lint/format, typecheck, tests, build).
6. **Open a pull request** with a clear description and test evidence.
7. **Address review comments** with additional commits (do not force-push a shared branch).
8. **Merge** using the team's strategy (squash recommended).

---

## 5. Bug fixes

- Reproduce first; write a failing test when practical.
- Keep the fix minimal and targeted.
- Include the root cause in the PR description.
- Never "fix" a bug by weakening validation or tenant isolation.
- If the bug is security-related, follow §12 and coordinate privately before opening a public issue.

---

## 6. Frontend contribution workflow

### 6.1 Setup

```bash
cd products/healthcare/dental/dentalpilot-ai/frontend
npm ci
npm start          # http://localhost:4200
```

### 6.2 Conventions

- Standalone components; `inject()` for services; signals for state.
- One feature folder per module; lazy-loaded `*.routes.ts`.
- API calls go through a `*.service.ts` using `API_ENDPOINTS` and `environment.apiBaseUrl`.
- No cross-feature imports; shared code goes in `core/` or `shared/`.
- Tailwind utility classes; no component stylesheets.
- Use `formFieldClass()` for form controls.
- Handle loading and error states; use `NotificationService` for toasts.
- Do not store tokens anywhere except `TokenStorageService`.

### 6.3 Checks

```bash
npx prettier --check "src/**/*.{ts,html,css}"
npm test
npm run build
```

### 6.4 Adding a feature

```bash
ng generate component features/my-feature/my-page --standalone
```

Then add a `my-feature.routes.ts` and register it in `app.routes.ts` with `authGuard`.

---

## 7. Backend contribution workflow

### 7.1 Setup

```bash
cd products/healthcare/dental/dentalpilot-ai/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set JWT_SECRET
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Or use the Docker stack:

```bash
docker compose -f docker-compose.local.yml up -d --build
```

### 7.2 Conventions

- Routers under `app/routers/`; register in `app/main.py` with `prefix="/api/v1"`.
- Pydantic schemas in `app/schemas/`; use `CamelModel` for API DTOs.
- ORM models in `app/models/`; import them in `app/models/__init__.py` so Alembic sees them.
- Business logic in `app/services/` when it is reused or complex.
- **Every tenant query must filter by `current_user.clinic_id`** (and `branch_id` for staff).
- Use the dependency aliases: `CurrentUser`, `CurrentPatient`, `RequireOwner`, `RequireSuperAdmin`, `DbSession`.
- Do not log passwords, tokens, patient records, or payment secrets.
- Return the standard error shape (`{statusCode, message, errors?}`).
- Keep `CatchAllExceptionMiddleware` registered before `CORSMiddleware`.

### 7.3 Checks

```bash
pytest tests/ -q
```

Add tests for new endpoints, validation, tenant scoping and error paths.

---

## 8. Database migration conventions

### 8.1 Creating a migration

```bash
cd backend
source .venv/bin/activate

# After editing a model
alembic revision --autogenerate -m "add <table-or-column>"

# Review alembic/versions/<rev>_<slug>.py before applying
alembic upgrade head
```

### 8.2 Rules

- **One logical change per revision.**
- **Review autogenerated code** — autogenerate does not detect everything (renames, indexes, constraints).
- **Test both directions** on PostgreSQL:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

- **Never edit a migration that has already been applied** to a shared environment; add a new revision instead.
- **Never destructive without approval.** Dropping/renaming columns or tables requires an explicit migration plan, a backup and sign-off.
- Prefer **expand/contract**: add the new column/table, deploy code that writes both, backfill, then remove the old column in a later release.
- Name constraints explicitly (SQLite batch mode requires names; Postgres benefits from predictable names).
- Keep migrations backward-compatible with the previous application version during rolling deploys.

### 8.3 Local reset (local only)

```bash
# SQLite
rm backend/dentalpilot.db
alembic upgrade head
python scripts/seed_hierarchy.py

# Docker (DESTRUCTIVE — local volumes only)
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up -d --build
```

---

## 9. Test requirements

- **Backend:** add or update `pytest` tests for new endpoints, validation, tenant scoping, and error paths. Run `pytest tests/ -q`.
- **Frontend:** add Vitest specs for new services/components where practical. Run `npm test`.
- **Migrations:** test `upgrade`/`downgrade` on PostgreSQL.
- **Integration:** test Razorpay signature verification and webhook idempotency with fakes; never require live credentials.
- **Do not** commit real patient data, credentials or production dumps.

Current backend suites:

```
tests/test_healthcare_workflows.py
tests/test_native_operations_and_organizations.py
tests/test_email_outbox.py
```

---

## 10. Pull request expectations

A PR should include:

- **Summary** — what changed and why.
- **Type** — feature / fix / refactor / docs / chore.
- **Testing** — commands run and results.
- **Risk** — migrations, API changes, security implications.
- **Screenshots** — for UI changes.
- **Checklist**:
  - [ ] Tests added/updated and passing.
  - [ ] `npm run build` / `pytest` pass.
  - [ ] No secrets or `.env` files.
  - [ ] No real patient data.
  - [ ] Migrations reviewed and reversible where possible.
  - [ ] Tenant isolation preserved.
  - [ ] Docs updated if behaviour changed.

Keep PRs focused; split large changes.

---

## 11. Code review checklist

**Correctness**

- [ ] Does it do what the PR says?
- [ ] Are edge cases handled?
- [ ] Are errors returned in the standard shape?

**Security**

- [ ] Server-side validation (Pydantic/Zod equivalent).
- [ ] Tenant scoping on every query.
- [ ] No secrets in logs or responses.
- [ ] Webhook signatures verified.
- [ ] File uploads validated (type/size) and stored privately.

**Data**

- [ ] Migration reviewed; no destructive change without approval.
- [ ] Indexes added for new query patterns.
- [ ] Idempotency for retries/webhooks.

**Tests**

- [ ] New behaviour covered.
- [ ] Existing tests still pass.

**Operability**

- [ ] Logs are useful and do not leak PII.
- [ ] Health checks still pass.
- [ ] Backward compatible with the previous release.

---

## 12. Security requirements

- **Never commit secrets** — `.env`, `.env.local`, `.env.production`, `.env.staging`, keys, tokens. The root `.gitignore` ignores them.
- **Never use real patient data** in tests, fixtures, screenshots or logs.
- **Validate on the server** — client-side validation is a hint only.
- **Enforce tenant isolation** — every tenant query filters by `clinic_id` (and `branch_id` for staff).
- **Audit sensitive actions** — use `audit()` for record access, modifications, exports, consent changes, billing and organisation changes.
- **Keep dependencies pinned** — `requirements.txt` and `package-lock.json` are the source of truth; review updates.
- **Protect storage** — S3 buckets private; SSE/KMS; presigned URLs short-lived.
- **Verify webhooks** — Razorpay signature on every webhook.
- **Report vulnerabilities privately** — do not open a public issue with exploit details.

---

## 13. Release and versioning (recommended)

- **Semantic Versioning** `MAJOR.MINOR.PATCH`.
- Tag releases: `vX.Y.Z`.
- Update `RELEASE_NOTES.md` and `package.json` version.
- Migrations must be backward-compatible with the previous release.
- Rollback = redeploy the previous image/tag; schema changes are forward-only.

---

## 14. Definition of done

- [ ] Code implemented and reviewed.
- [ ] Tests added/updated and passing.
- [ ] Lint/format/build pass.
- [ ] Migrations reviewed and tested.
- [ ] Docs updated.
- [ ] No secrets, no real patient data.
- [ ] Tenant isolation and audit requirements met.
- [ ] PR merged; branch deleted.

---

## 15. Related documentation

- [`README.md`](README.md)
- [`ENVIRONMENT_GUIDE.md`](ENVIRONMENT_GUIDE.md)
- [`RAILWAY_DEPLOYMENT.md`](RAILWAY_DEPLOYMENT.md)
- [`backend/README.md`](backend/README.md)
- [`frontend/README.md`](frontend/README.md)
- [`AUDIT/PRODUCT_IMPLEMENTATION_AUDIT.md`](AUDIT/PRODUCT_IMPLEMENTATION_AUDIT.md)