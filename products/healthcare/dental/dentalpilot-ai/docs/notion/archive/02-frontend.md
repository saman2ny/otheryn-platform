# DentalPilot AI — Frontend

Angular 21 frontend for DentalPilot AI, an AI-powered marketing platform for dental clinics. This app covers the MVP modules from the product blueprint: Authentication, Clinic Profile, AI Content Generator, Content Calendar, Export Content, Subscription & Billing, and a Dashboard.

Every feature service calls a REST contract defined in `src/app/core/constants/api-endpoints.const.ts` — see the Backend doc for the FastAPI implementation of that contract. Run both together (backend on port 8000, then `npm start` here) and the app works end-to-end against a real database.

## Tech stack

- **Angular 21** — standalone components, zoneless change detection, signals
- **Tailwind CSS v4** — utility-first styling, no component-level stylesheets
- **RxJS** — HTTP and async event streams
- **Vitest** — unit test runner (Angular's default as of v21)
- **TypeScript** — strict mode, strict templates

## Getting started

```bash
npm install
npm start          # ng serve — http://localhost:4200
```

Other commands:

```bash
npm run build       # production build → dist/dentalpilot-ai
npm run watch        # dev build, watch mode
npm test              # run unit tests (Vitest)
npx prettier --check "src/**/*.{ts,html,css}"   # formatting check
```

## Environment configuration

| File | Used for | `apiBaseUrl` |
|---|---|---|
| `src/environments/environment.ts` | `ng serve`, dev builds | `http://localhost:8000/api/v1` |
| `src/environments/environment.prod.ts` | `ng build` (production config) | `https://api.dentalpilot.in/api/v1` |

`angular.json`'s production configuration swaps the file via `fileReplacements`, so components always just import `environment` from `./environments/environment` and get the right value for the build.

## Architecture

```
src/app/
  core/                  — app-wide singletons, not feature-specific
    constants/           — api-endpoints.const.ts — the REST contract
    models/              — shared TypeScript interfaces/DTOs
    services/            — AuthService, TokenStorageService, NotificationService, LoadingService
    interceptors/        — auth (attaches bearer token), error, loading
    guards/               — authGuard, guestGuard

  shared/                — reusable, feature-agnostic building blocks
    ui/                  — PageHeader, EmptyState, StatCard, ToastContainer, LoadingBar
    forms/               — formFieldClass() — shared Tailwind class logic for form controls
    razorpay.d.ts        — ambient types for the global Razorpay (script-loaded, not npm)

  layout/
    shell/               — authenticated app shell (sidebar nav + topbar)
    auth-layout/         — centered card layout for login/register/forgot-password

  features/              — one folder per MVP module, each lazy-loaded via its own *.routes.ts
    auth/                — login, register, forgot-password
    dashboard/
    clinic-profile/
    content-generator/
    content-calendar/
    export-content/
    billing/
```

Each feature folder is self-contained: a `*.routes.ts` (lazy-loaded from `app.routes.ts`), a `*.service.ts` (HttpClient calls against `API_ENDPOINTS`), and the page component(s). Nothing outside `core/` and `shared/` is imported across feature boundaries.

State is signals-based throughout — no NgRx or other state library, since a lightweight per-feature signal service was enough for this app's scope.

## Styling

Global styles live in `src/styles.css` (just the Tailwind import plus one custom `@keyframes` for the loading bar). There are no per-component stylesheets — every component uses Tailwind utility classes directly in its template. The brand palette maps onto Tailwind's built-in `teal`/`slate`/`green`/`red`/`blue`/`amber` scales, so there's no custom theme config to maintain.

## Payments

The billing page (`features/billing/`) uses Razorpay's **Standard Checkout** — a hosted modal, not a redirect. `checkout.js` is loaded globally via a `<script>` tag in `index.html` (not an npm package), so `shared/razorpay.d.ts` declares ambient types for the global `Razorpay` class it exposes.

**Flow** (`billing.ts`): `selectPlan()` calls the backend to create an order → if the plan is free, it's applied immediately with no modal → otherwise `openRazorpayCheckout()` constructs `new Razorpay({...})` with the order details the backend returned (`orderId`, `amount`, `currency`, `keyId`) and calls `.open()`. On success, the modal's `handler` callback sends the three Razorpay-provided values (`razorpay_order_id`, `razorpay_payment_id`, `razorpay_signature`) to the backend's verify endpoint, which re-derives the signature server-side before applying the plan. Modal dismissal and `payment.failed` are both handled explicitly so the "Choose plan" button never gets stuck in a loading state.

## Routing

Portal URLs, relative to `http://localhost:4200` in dev:

**Public** (guarded by `guestGuard` — redirects to `/dashboard` if already logged in)

| URL | Page |
|---|---|
| `/auth/login` | Sign in |
| `/auth/register` | Create account |
| `/auth/forgot-password` | Password reset |

**Authenticated** (behind the app shell, guarded by `authGuard` — redirects to `/auth/login` if not logged in)

| URL | Page |
|---|---|
| `/dashboard` | Dashboard (also the default landing page — `/` redirects here) |
| `/clinic-profile` | Clinic Profile |
| `/content-generator` | AI Content Generator |
| `/content-calendar` | Content Calendar |
| `/export-content` | Export Content |
| `/billing` | Subscription & Billing |

**Fallback**

| URL | Behavior |
|---|---|
| anything else (`/**`) | redirects to `/` → `/dashboard` (or `/auth/login` if not authenticated) |
