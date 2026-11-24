# DentalPilot AI — Frontend

Angular 21 single-page application. This is a **concise component guide**; the authoritative architecture is in [`../docs/notion/TECHNICAL_ARCHITECTURE.md`](../docs/notion/TECHNICAL_ARCHITECTURE.md) and the full setup/deployment is in [`../docs/notion/SETUP_AND_DEPLOYMENT.md`](../docs/notion/SETUP_AND_DEPLOYMENT.md).

## Stack

- Angular `^21.2.0` — standalone components, zoneless, signals.
- TypeScript `~5.9.2` (strict), Tailwind CSS `^4.3.3`.
- Vitest `^4.0.8` for unit tests; Prettier for formatting.
- Node 22 LTS recommended (20.19+ minimum), npm 11.
- Tested locally on Node v24.16.0 / npm 11.20.0; lockfile resolves Angular 21.2.18, TypeScript 5.9.3, Vitest 4.1.10. Deployment uses `node:20-alpine` (floating; must be ≥20.19); recommended Node 22 LTS.

## Commands

```bash
cd products/healthcare/dental/dentalpilot-ai/frontend
npm ci
npm start          # ng serve → http://localhost:4200
npm run build      # production build → dist/dentalpilot-ai/browser/
npm test           # Vitest (add --watch=false for a single run)
npx prettier --check "src/**/*.{ts,html,css}"
```

There is **no `lint` script**.

## Architecture

```
src/app/
├── core/
│   ├── constants/   # API_ENDPOINTS (REST contract)
│   ├── guards/      # authGuard, guestGuard
│   ├── interceptors/# auth, error, loading
│   ├── models/      # TypeScript DTOs
│   └── services/    # AuthService, TokenStorageService, NotificationService, LoadingService
├── shared/
│   ├── forms/       # formFieldClass()
│   ├── ui/          # PageHeader, EmptyState, StatCard, ToastContainer, LoadingBar
│   └── razorpay.d.ts
├── layout/          # shell, auth-layout
└── features/        # lazy-loaded modules
```

Features: `auth`, `dashboard`, `clinic-profile`, `content-generator`, `content-calendar`, `clinic-growth-os`, `dental-operations`, `organization-management`, `export-content`, `billing`, `dentalpilot-workflows`, `patient-portal` (public), `staff-invitation` (public).

- State: signals only; no NgRx.
- Routing: lazy `*.routes.ts`; `authGuard` for authenticated routes, `guestGuard` for auth pages; `/patient-portal` and `/staff-invitation` are public.
- Interceptors: `authInterceptor` (Bearer), `loadingInterceptor`, `errorInterceptor` (toasts; logout on 401 except patient portal).

## Environment

| File | Build | `apiBaseUrl` |
|---|---|---|
| `src/environments/environment.ts` | `ng serve` / dev | `http://localhost:8000/api/v1` |
| `src/environments/environment.prod.ts` | `ng build` | `https://api.dentalpilot.in/api/v1` |

`angular.json` swaps the file via `fileReplacements`. **Build-time only** — Railway variables do not change the bundle.

## Hot reload

`ng serve` watches source and updates the browser on `.ts` / `.html` / `.css` changes. Verified output includes `Watch mode enabled. Watching for file changes...`. No manual restart is required. In Docker on macOS, add `--poll 1000` (see the setup guide).

## Production deployment (summary)

Railway service → root `frontend/` → Dockerfile (`node:20-alpine` → `nginx:alpine`) → Nginx serves the SPA and proxies `/api/` to `https://api.dentalpilot.in` → custom domain + TLS.

Full steps, verification and rollback: [`../docs/notion/SETUP_AND_DEPLOYMENT.md`](../docs/notion/SETUP_AND_DEPLOYMENT.md).

## API contract

The REST contract is [`src/app/core/constants/api-endpoints.const.ts`](src/app/core/constants/api-endpoints.const.ts). It mirrors the FastAPI routers documented in [`TECHNICAL_ARCHITECTURE.md`](../docs/notion/TECHNICAL_ARCHITECTURE.md).

## Links

- [`../README.md`](../README.md) — project entry point.
- [`../docs/notion/SETUP_AND_DEPLOYMENT.md`](../docs/notion/SETUP_AND_DEPLOYMENT.md) — local + production.
- [`../docs/notion/TECHNICAL_ARCHITECTURE.md`](../docs/notion/TECHNICAL_ARCHITECTURE.md) — architecture.
- [`../docs/notion/BUSINESS_PROPOSAL.md`](../docs/notion/BUSINESS_PROPOSAL.md) — business.
- [`../RELEASE_NOTES.md`](../RELEASE_NOTES.md) — release history.