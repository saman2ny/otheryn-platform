# Phase 1 — Patient Record Intelligence Completion Record

**Date:** 2026-11-24
**Status:** **COMPLETE for Clinic Owner and Patient (read-only); PARTIAL for Super Admin (no dedicated admin UI)**
**Scope:** Patient editing, medical history, dental history, emergency contacts, duplicate detection, revision history, server-side search/pagination, patient-portal read-only access.

> This record is a dated completion record. It does not rewrite the historical audit baseline.

---

## 1. What was already complete (verified)

- Patient registration (`POST /patients`) and list (`GET /patients`).
- Patient get by id (`GET /patients/{id}`).
- Patient partial update (`PATCH /patients/{id}`) with validation, clinic/branch scoping, audit and revision snapshot.
- Medical history, dental history, emergency contacts (JSON fields + edit form).
- Duplicate detection (`GET /patients/duplicates`).
- Revision history (`GET /patients/{id}/revisions`).
- Migration `20261124000000_patient_intelligence` applied (`alembic current` = `20261124000000 (head)`).
- 58 backend tests passing at the start of this phase.

## 2. What was incomplete

- No server-side patient search/pagination (`GET /patients` returned all rows; the UI filtered client-side).
- No revision-history UI.
- No patient-portal read-only access to medical history, dental history or emergency contacts.
- No dedicated Super Admin patient-oversight UI (only the shared clinic workflows UI).

## 3. What was implemented in this phase

### Backend
- `GET /api/v1/healthcare/patients` supports `q`, `limit`, `offset` (server-side search + pagination, clinic/branch scoped; **super_admin can list across clinics** and optionally filter by `clinic_id`).
- `POST /api/v1/healthcare/patients` now **prevents accidental duplicates** (409 when the same name + email exists in the clinic).
- `PATCH /api/v1/healthcare/patients/{patient_id}` **merges** `medical_history` and `dental_history` objects, so a partial update does not wipe other keys.
- New patient-portal read-only endpoints (patient-scoped via `CurrentPatient`):
  - `GET /api/v1/patient-portal/medical-history`
  - `GET /api/v1/patient-portal/dental-history`
  - `GET /api/v1/patient-portal/emergency-contacts`
- Each portal read writes an audit event.

### Frontend
- Patient search input + server-side search.
- "Load more" pagination (increments the page size and reloads).
- "History" action + revision list.
- Duplicate feedback on registration (409 → clear message).
- Patient portal "Health profile" read-only section (medical/dental/emergency).
- API contract additions for the new endpoints.

### Tests
- New `test_patient_management.py` cases:
  - patient search + pagination
  - patient-portal medical history
  - patient-portal dental history
  - patient-portal emergency contacts
  - patient-portal cannot read another patient
  - duplicate patient blocked (409)
  - medical history partial merge
  - super_admin can list across clinics

## 4. Role verification

### Super Admin

| Capability | UI | API | DB persistence | RBAC | E2E | Status |
|---|---|---|---|---|---|---|
| Patient directory | ✅ shared workflows | ✅ | ✅ | ✅ super_admin (all clinics) | Not run | COMPLETE |
| Patient registration | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Patient profile | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Demographic editing | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Medical history | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Dental history | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Emergency contacts | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Duplicate detection | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Revision history | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Cross-clinic oversight | ⚠️ via directory | ✅ | ✅ | ✅ | Not run | PARTIAL (no dedicated admin dashboard) |

### Clinic Owner

| Capability | UI | API | DB persistence | RBAC | E2E | Status |
|---|---|---|---|---|---|---|
| Patient directory | ✅ | ✅ | ✅ | ✅ clinic/branch | Not run | COMPLETE |
| Patient registration | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Patient profile | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Demographic editing | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Medical history | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Dental history | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Emergency contacts | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Duplicate detection | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Revision history | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Cross-clinic isolation | ✅ | ✅ | ✅ | ✅ tested | Not run | COMPLETE |

### Patient

| Capability | UI | API | DB persistence | Ownership | E2E | Status |
|---|---|---|---|---|---|---|
| View own profile | ✅ | ✅ | ✅ | ✅ patient | Not run | COMPLETE |
| View medical history | ✅ | ✅ | ✅ | ✅ patient | Not run | COMPLETE |
| View dental history | ✅ | ✅ | ✅ | ✅ patient | Not run | COMPLETE |
| View emergency contacts | ✅ | ✅ | ✅ | ✅ patient | Not run | COMPLETE |
| Update medical history | ❌ | ❌ | — | — | — | MISSING (clinician-managed by design) |
| Update dental history | ❌ | ❌ | — | — | — | MISSING (clinician-managed by design) |
| Update emergency contacts | ❌ | ❌ | — | — | — | MISSING (clinician-managed by design) |
| View records/shares | ✅ | ✅ | ✅ | ✅ | Not run | COMPLETE |
| Access another patient | — | — | — | — | — | BLOCKED (tested) |

## 5. Cross-module integration

| Module | Patient linkage | Status |
|---|---|---|
| Treatment plans | `patient_id` FK | COMPLETE |
| Clinical records | `patient_id` FK | COMPLETE |
| Consent | `patient_id` FK | COMPLETE |
| Patient Passport | `patient_portal_accounts.patient_id` | COMPLETE |
| Recall | `patient_id` FK | COMPLETE |
| Patient portal | `patient_portal_accounts` | COMPLETE |

The new fields are additive; existing relationships are unchanged.

## 6. Tests

- **Backend: 66 passed, 0 failed** (Python 3.12 in Docker).
- **Frontend: build PASS, 1/1 test PASS.**
- **Browser E2E: NOT EXECUTED** (no Playwright browsers installed).
- **Live API check:** duplicate prevention verified (201 → 409).

## 6.1 Interactive product tours (Shepherd.js)

- **Library:** `shepherd.js` **16.0.0** (compatible with Angular 21; no competing tour library).
- **Role-specific tours:** `super_admin` (12 steps) and `owner` (12 steps), covering dashboard, directory, registration, profile, editing, medical/dental history, emergency contacts, duplicate detection, revision history, filters, associations, consent/Passport and audit.
- **Entry points:** auto-starts on first login (if not completed/skipped) and a **"Guided tour"** button in the shell topbar for manual start/restart.
- **Per-user persistence:** `localStorage` keys `dp_tour_<userId>_<role>_1_completed` / `_skipped` — two different users with the same role do **not** share state. No patient data is stored.
- **Selector validation:** missing selectors are logged to the console (`[DentalPilot tour] Missing target for step ...`) and the step is shown centered instead of failing silently.
- **Behaviour:** next/previous, skip, finish, Esc, route navigation between steps, selector highlighting, graceful recovery.
- **Files:** `frontend/src/app/core/services/tour.service.ts`, `shell.ts`, `shell.html`, `styles.css`, `package.json`/`package-lock.json`, `e2e/tour.spec.ts`.
- **Validation:**
  - `npm run build` ✅
  - `npm test` ✅ (1/1)
  - **Playwright E2E: 2/2 passed** — Super Admin tour starts and skips; Clinic Owner tour starts, navigates, skips, persists, and does not auto-start after refresh.
- **Local Docker note:** the `frontend_node_modules` named volume must be refreshed after adding a dependency (`docker compose ... exec frontend npm install`).

---

## 6.2 Runtime fixes (2026-11-24)

- **Fixed `/api/v1/clinic/onboarding` 500** — `OnboardingStep` was used but not imported in `app/routers/clinic.py`. Added the import. Endpoint now returns **200**.
- **Fixed `/api/v1/analytics/operational` 500** — the query referenced `User.is_active`, which does not exist on the `User` model. Removed the filter. Endpoint now returns **200**.
- **Added `backend/scripts/seed_demo_data.py`** — local/demo-only, idempotent, refuses `APP_ENVIRONMENT=production`. Seeds 3 fictional patients, 1 demo post and 1 scheduled event for the demo clinic.
- **Verified dashboard data:** `/dashboard/summary` now returns `contentGeneratedThisMonth: 1`, `postsScheduledUpcoming: 1`, and the demo content/event; patient list returns 4 (1 pre-existing + 3 demo).
- **Regression:** backend **66 passed**, frontend build/test pass.

---

## 7. Remaining limitations

- No dedicated Super Admin patient-oversight UI (cross-clinic).
- No patient self-service edits for medical/dental history or emergency contacts (clinician-managed by design).
- No automatic duplicate merge (by design).
- No browser E2E.
- No server-side revision-history UI beyond the new patient revision list (the list is implemented).

## 8. Phase 1 status

- **Clinic Owner:** COMPLETE (all Phase 1 capabilities implemented and unit-tested).
- **Patient:** COMPLETE for read-only access; updates are clinician-managed.
- **Super Admin:** PARTIAL — shares the clinic workflows UI; no dedicated cross-clinic admin UI.
- **Overall:** **COMPLETE for the core patient-record workflow**, with the Super Admin UI and E2E as remaining items.

No database volumes were deleted, no migrations were rewritten, and no commit/push/deploy occurred.