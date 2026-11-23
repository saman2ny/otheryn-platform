# Otheryn Monorepo

Unified monorepo for the Otheryn platform and its products. This repository was
assembled in Phase 1 (repository integration only) and contains the existing
codebases with their full Git history.

## Layout (as of Phase 1)

- `apps/web/` — Otheryn marketing website + lead-capture API
  (Vite + React 19 SPA; Express 5 server under `apps/web/server`; Supabase).
- `products/healthcare/dental/dentalpilot-ai/` — DentalPilot AI, the first enabled
  product (FastAPI backend + Angular frontend + Alembic migrations).

## Status

- DentalPilot AI: enabled.
- All other specialties and industries: not present yet (disabled / planned).

## Proposed / future (NOT implemented in this repository)

- `platform/` (identity, organizations, tenancy, authorization, policy-governance,
  configuration, execution, assurance, intelligence, ecosystem) — proposed.
- Additional healthcare specialties and non-healthcare industries — proposed.
- UETI capabilities (governed execution, evidence, verification, accountability,
  audit, AI agents, robotics) — proposed / future.

No UETI capability is implemented by virtue of this structure. Do not treat the
architecture plan as a statement of implemented functionality.