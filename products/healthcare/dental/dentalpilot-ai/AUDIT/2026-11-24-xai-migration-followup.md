# Follow-up Audit — 2026-11-24 (xAI Grok migration)

**Type:** Dated follow-up. This document does **not** rewrite [`PRODUCT_IMPLEMENTATION_AUDIT.md`](PRODUCT_IMPLEMENTATION_AUDIT.md); that file remains the historical baseline.

## Scope

Migration of the active AI provider from Anthropic Claude to **xAI Grok** across DentalPilot AI.

## What changed

| Area | Change |
|---|---|
| Backend provider | `app/services/ai_content.py` and `app/services/clinical_notes.py` now use the OpenAI-compatible xAI API (`https://api.x.ai/v1`, model `grok-4.7`). |
| Configuration | `app/core/config.py`: `XAI_API_KEY`, `XAI_MODEL`, `XAI_BASE_URL` replace `ANTHROPIC_*`. |
| Routers | `content.py`, `operations.py`, `clinic.py` use `settings.xai_*`; `generation_source` is now `"xai"`; audit provider `"xai"`. |
| Dependencies | `requirements.txt`: `anthropic==0.117.0` removed; `openai>=1.0` added. |
| Environment templates | `.env.local.example`, `.env.staging.example`, `.env.production.example`, `backend/.env.example` now use `XAI_*`. |
| Compose | `docker-compose.yml` backend/workers pass `XAI_*`. |
| Deploy | `deploy.sh` no longer requires `ANTHROPIC_API_KEY` (AI is optional). |
| Frontend | `operations.model.ts` `generationSource: 'clinician' \| 'xai'`; `dental-operations.html` labels updated to xAI Grok. |
| Tests | Existing test updated to `xai_api_key` / `generationSource == "xai"`; new `tests/test_ai_provider.py` covers success, model config, missing key, malformed JSON, invalid shape, rate limit, timeout, server error, clinical note success, and approval gate. |
| Docs | `README.md`, `TECHNICAL_ARCHITECTURE.md`, `SETUP_AND_DEPLOYMENT.md`, `backend/README.md`, `ENVIRONMENT_GUIDE.md` updated; Mermaid provider node now `xAI Grok`. |

## Test results (executed)

- Backend: **40 passed, 0 failed** (Python 3.12 in Docker).
- Frontend: see the final report for the actual `npm test` / `npm run build` results.
- Compose: local/production/staging `docker compose config` valid.

## Intentionally retained historical references

- `AUDIT/PRODUCT_IMPLEMENTATION_AUDIT.md` — historical baseline (Anthropic references remain as historical evidence).
- `docs/notion/archive/01-project-overview.md`, `02-frontend.md`, `03-backend.md` — archived historical documents.
- `RELEASE_NOTES.md` — no Anthropic references; unchanged.

## Remaining blockers (unchanged by this migration)

- P0-2: SQLite migration `e78cbd0fad9c` fails (`Constraint must have a name`).
- P0-4: No application-level rate limiting.
- P0-5: Nested CI workflow is not at the repository root.
- P1: logout no-op, localStorage tokens, partial audit logging, untested subscription billing.
- P2: unpaginated lists, Redis provisioned but unused, Python version mismatch (Nixpacks 3.11 vs Dockerfile 3.12), no CSP.

No deployment, commit or push was performed.