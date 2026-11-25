export type DocSectionId =
  | 'getting-started'
  | 'concepts'
  | 'architecture'
  | 'products'
  | 'api'
  | 'integrations'
  | 'security'
  | 'troubleshooting'
  | 'changelog';

export type DocBlock =
  | { type: 'paragraph'; text: string }
  | { type: 'heading'; id: string; text: string }
  | { type: 'list'; items: string[] }
  | { type: 'code'; language: string; label?: string; code: string }
  | { type: 'callout'; tone: 'info' | 'warning' | 'planned'; title: string; text: string }
  | { type: 'table'; columns: string[]; rows: string[][] };

export type DocArticle = {
  id: string;
  slug: DocSectionId;
  path: string;
  navLabel: string;
  title: string;
  description: string;
  updated: string;
  blocks: DocBlock[];
};

export const DOC_ARTICLES: DocArticle[] = [
  {
    id: 'getting-started',
    slug: 'getting-started',
    path: '/documentation/getting-started',
    navLabel: 'Getting Started',
    title: 'Getting Started',
    description:
      'How to navigate Otheryn documentation, understand current implementation status, and find the right resources for platform, product, and operational workflows.',
    updated: '2026-11-24',
    blocks: [
      {
        type: 'paragraph',
        text:
          'Otheryn documentation is the reference destination for the public website, platform concepts, implemented product surfaces, and operational guidance. This documentation only describes capabilities that exist in the repository or are explicitly marked as planned.',
      },
      {
        type: 'callout',
        tone: 'info',
        title: 'Documentation scope',
        text:
          'Live/implemented items are documented with concrete routes, repository locations, or observed behavior. Capabilities described in UETI platform strategy but not implemented in this repository are labeled Planned.',
      },
      { type: 'heading', id: 'what-is-otheryn', text: 'What is Otheryn' },
      {
        type: 'paragraph',
        text:
          'Otheryn is presented as Universal Execution & Trust Infrastructure (UETI): a foundation for governed actions, verifiable execution, and accountable outcomes. The public website communicates this platform direction, while DentalPilot AI is the first enabled healthcare product in the monorepo.',
      },
      { type: 'heading', id: 'current-repository-layout', text: 'Current repository layout' },
      {
        type: 'table',
        columns: ['Area', 'Path', 'Status', 'Purpose'],
        rows: [
          ['Public website', 'apps/web', 'Implemented', 'Otheryn marketing website, contact/booking flows, and this documentation centre.'],
          ['DentalPilot AI', 'products/healthcare/dental/dentalpilot-ai', 'Implemented', 'Dental practice product with frontend, backend, workers, migrations, and E2E tests.'],
          ['Platform capability model', 'apps/web/src/data/ueti.ts', 'Planned/communicated', 'UETI capability definitions and status labels used by public website content.'],
        ],
      },
      { type: 'heading', id: 'local-website-development', text: 'Run the public website locally' },
      {
        type: 'paragraph',
        text:
          'The Otheryn website is a Vite + React + TypeScript application under apps/web. Use the web app scripts from that package.',
      },
      {
        type: 'code',
        language: 'bash',
        label: 'Install and run web app',
        code: `cd apps/web
npm install
npm run dev`,
      },
      {
        type: 'code',
        language: 'bash',
        label: 'Run web app and API server together',
        code: `cd apps/web
npm run dev:all`,
      },
      { type: 'heading', id: 'documentation-conventions', text: 'Documentation conventions' },
      {
        type: 'list',
        items: [
          'Implemented: Feature or route exists in code and can be validated locally.',
          'Planned: Feature is part of platform direction but not implemented in this repository.',
          'External dependency: Behavior depends on configured services such as Supabase, Resend, or deployment infrastructure.',
        ],
      },
    ],
  },
  {
    id: 'concepts',
    slug: 'concepts',
    path: '/documentation/concepts',
    navLabel: 'Platform Concepts',
    title: 'Platform Concepts',
    description:
      'Core Otheryn concepts, including UETI capability areas, status model, and how implemented products relate to planned platform infrastructure.',
    updated: '2026-11-24',
    blocks: [
      {
        type: 'paragraph',
        text:
          'Platform concepts describe the model Otheryn communicates publicly and the boundaries between implemented product behavior and planned platform infrastructure.',
      },
      { type: 'heading', id: 'ueti', text: 'Universal Execution & Trust Infrastructure' },
      {
        type: 'paragraph',
        text:
          'UETI is the platform framing used by the Otheryn website. It defines five capability areas: Identity and Authorization, Policy and Governance, Execution and Orchestration, Evidence and Verification, and Accountability and Audit.',
      },
      {
        type: 'callout',
        tone: 'planned',
        title: 'Planned platform capabilities',
        text:
          'The UETI capability model is present in website content (apps/web/src/data/ueti.ts) and all five capabilities are currently marked planned. Do not treat these as deployed platform services unless implementation evidence is added.',
      },
      { type: 'heading', id: 'capability-statuses', text: 'Capability status model' },
      {
        type: 'table',
        columns: ['Status', 'Meaning', 'How to use in docs'],
        rows: [
          ['Live', 'Implemented and available in the product/repository.', 'Document with route, API, or file evidence.'],
          ['Planned', 'Part of roadmap or platform direction, not implemented.', 'Label clearly as Planned and avoid operational claims.'],
          ['Coming Soon', 'Publicly announced but not yet available.', 'Label clearly and do not provide unavailable setup steps.'],
        ],
      },
      { type: 'heading', id: 'product-vs-platform', text: 'Product vs platform' },
      {
        type: 'list',
        items: [
          'Platform concepts define shared trust and execution capabilities intended to span products.',
          'DentalPilot AI is an implemented healthcare product with its own frontend, backend APIs, database migrations, and worker processes.',
          'The public website is an implemented communication and lead-capture surface; it is not evidence that all UETI platform capabilities are live.',
        ],
      },
      { type: 'heading', id: 'evidence-first-documentation', text: 'Evidence-first documentation' },
      {
        type: 'paragraph',
        text:
          'When documenting Otheryn behavior, prefer repository evidence: routes, components, tests, API routers, schemas, migrations, and configuration files. If a capability cannot be verified, mark it as planned or unknown.',
      },
    ],
  },
  {
    id: 'architecture',
    slug: 'architecture',
    path: '/documentation/architecture',
    navLabel: 'Architecture',
    title: 'Architecture',
    description:
      'High-level architecture for the Otheryn monorepo, public website, and implemented DentalPilot AI product surfaces.',
    updated: '2026-11-24',
    blocks: [
      {
        type: 'paragraph',
        text:
          'The repository contains multiple application surfaces. This page documents the implemented architecture visible in source control and clearly separates planned platform capabilities.',
      },
      { type: 'heading', id: 'monorepo-structure', text: 'Monorepo structure' },
      {
        type: 'code',
        language: 'text',
        label: 'Top-level layout',
        code: `otheryn-platform/
  apps/
    web/                 # Otheryn public website (Vite + React)
  products/
    healthcare/
      dental/
        dentalpilot-ai/  # DentalPilot AI product (Angular + FastAPI)`,
      },
      { type: 'heading', id: 'web-architecture', text: 'Public website architecture' },
      {
        type: 'table',
        columns: ['Layer', 'Implementation', 'Notes'],
        rows: [
          ['Frontend', 'React 19, React Router, Vite, Tailwind CSS 4', 'Routes defined in apps/web/src/App.tsx.'],
          ['Styling', 'Global design tokens in apps/web/src/index.css', 'Preserves Otheryn paper/ink/forest visual system and spatial surfaces.'],
          ['Server', 'Express + TSX server', 'scripts: npm run server / dev:all / start.'],
          ['Validation/tests', 'Zod, oxlint, TSX tests', 'Test scripts exist in apps/web/package.json; run in apps/web environment.'],
        ],
      },
      { type: 'heading', id: 'dentalpilot-architecture', text: 'DentalPilot AI architecture (implemented)' },
      {
        type: 'table',
        columns: ['Component', 'Implementation', 'Status'],
        rows: [
          ['Frontend', 'Angular app under products/healthcare/dental/dentalpilot-ai/frontend', 'Implemented'],
          ['Backend', 'FastAPI app under backend/app, Alembic migrations', 'Implemented'],
          ['Workers', 'Python workers under backend/app/workers', 'Implemented'],
          ['Local orchestration', 'docker-compose.local.yml', 'Implemented for local dev'],
          ['Guided tour', 'Shepherd.js tour service and Playwright E2E', 'Implemented'],
        ],
      },
      { type: 'heading', id: 'planned-platform-architecture', text: 'Planned UETI platform architecture' },
      {
        type: 'callout',
        tone: 'planned',
        title: 'Not yet implemented as shared runtime services',
        text:
          'Identity and authorization, policy/governance, execution/orchestration, evidence/verification, and accountability/audit are documented as platform capabilities on the website but are not implemented as shared UETI runtime services in this repository.',
      },
    ],
  },
  {
    id: 'products',
    slug: 'products',
    path: '/documentation/products',
    navLabel: 'Products & Modules',
    title: 'Products & Modules',
    description:
      'Implemented products and modules currently present in the Otheryn repository, with clear planned/not-live labeling where applicable.',
    updated: '2026-11-24',
    blocks: [
      {
        type: 'paragraph',
        text:
          'This section documents products and modules that have implementation evidence in the repository. Public roadmap items may appear on the website but are marked planned unless implemented.',
      },
      { type: 'heading', id: 'dentalpilot-ai', text: 'DentalPilot AI (Live product in repository)' },
      {
        type: 'paragraph',
        text:
          'DentalPilot AI is the implemented dental healthcare product under products/healthcare/dental/dentalpilot-ai. It includes Angular frontend, FastAPI backend, Postgres/Alembic data model, worker processes, and Docker local development.',
      },
      {
        type: 'table',
        columns: ['Module/Area', 'Evidence', 'Status'],
        rows: [
          ['Patient workflows', 'frontend/src/app/features/dentalpilot-workflows, backend healthcare routers/models', 'Implemented'],
          ['Guided tour', 'frontend/src/app/core/services/tour.service.ts, frontend/e2e/tour-regression.spec.ts', 'Implemented'],
          ['Docker local stack', 'docker-compose.local.yml', 'Implemented'],
          ['AI provider integration', 'backend Groq configuration/services as documented in prior audit records', 'Implemented/config-dependent'],
        ],
      },
      { type: 'heading', id: 'public-website', text: 'Otheryn public website (Implemented)' },
      {
        type: 'paragraph',
        text:
          'The public website under apps/web provides marketing and conversion pages, including platform, architecture, products, pricing, contact, booking, and legal routes.',
      },
      {
        type: 'list',
        items: [
          'Implemented routes include /, /platform, /architecture, /products, /solutions, /industries, /pricing, /contact, /book, /security, and legal pages.',
          'This Documentation Centre adds dedicated /documentation routes and does not reuse the Platform page component.',
          'Contact/booking/checkout behavior depends on configured backend endpoints and external services.',
        ],
      },
      { type: 'heading', id: 'planned-products', text: 'Planned product lines' },
      {
        type: 'callout',
        tone: 'planned',
        title: 'Roadmap only',
        text:
          'Additional healthcare product lines shown on public product/industry pages (IVF, dermatology, ophthalmology, cardiology, orthopaedics, plastic surgery, etc.) are planned/coming soon unless a dedicated implemented codebase and release evidence exists.',
      },
    ],
  },
  {
    id: 'api',
    slug: 'api',
    path: '/documentation/api',
    navLabel: 'API Reference',
    title: 'API Reference',
    description:
      'Reference for implemented API surfaces visible in this repository. Endpoints are documented only when present in source code.',
    updated: '2026-11-24',
    blocks: [
      {
        type: 'paragraph',
        text:
          'This API reference covers implemented or code-visible endpoints. It is not a complete public platform API specification because UETI shared platform APIs are not implemented in this repository.',
      },
      { type: 'heading', id: 'web-api', text: 'Public website API endpoints' },
      {
        type: 'paragraph',
        text:
          'The web app includes an Express server (apps/web/server) and Vite dev proxy for /api to http://127.0.0.1:3001. Exact behavior depends on server implementation and environment configuration.',
      },
      {
        type: 'code',
        language: 'http',
        label: 'Vite dev proxy (implemented)',
        code: `GET/POST /api/*
Proxy target: http://127.0.0.1:3001
Configured in: apps/web/vite.config.ts`,
      },
      { type: 'heading', id: 'dentalpilot-api', text: 'DentalPilot AI API (implemented product)' },
      {
        type: 'paragraph',
        text:
          'DentalPilot AI exposes FastAPI routes under backend/app/routers. The local stack runs backend on port 8000 in Docker compose. Use the product repository docs and OpenAPI/runtime when running the product for authoritative endpoint details.',
      },
      {
        type: 'table',
        columns: ['Endpoint/Area', 'Method', 'Status', 'Evidence'],
        rows: [
          ['/health', 'GET', 'Implemented', 'docker-compose healthcheck and local backend runtime.'],
          ['/api/v1/auth/*', 'POST/GET', 'Implemented', 'Backend auth routers/tests in DentalPilot AI.'],
          ['/api/v1/healthcare/patients*', 'GET/PATCH/POST', 'Implemented', 'Phase 1 patient record intelligence work and backend tests.'],
          ['UETI shared platform APIs', 'N/A', 'Planned', 'No shared UETI runtime API implementation in this repository.'],
        ],
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'API accuracy rule',
        text:
          'Do not publish undocumented endpoints as available. When extending this reference, link to router source, OpenAPI schema, or verified tests.',
      },
    ],
  },
  {
    id: 'integrations',
    slug: 'integrations',
    path: '/documentation/integrations',
    navLabel: 'Integrations',
    title: 'Integrations',
    description:
      'Implemented and configuration-dependent integrations visible in repository code and package configuration.',
    updated: '2026-11-24',
    blocks: [
      {
        type: 'paragraph',
        text:
          'Integrations listed here are based on dependencies and code present in the repository. Availability in a running environment depends on credentials, deployment configuration, and external service access.',
      },
      { type: 'heading', id: 'web-integrations', text: 'Public website integrations' },
      {
        type: 'table',
        columns: ['Integration', 'Evidence', 'Status', 'Notes'],
        rows: [
          ['Supabase', '@supabase/supabase-js dependency in apps/web/package.json', 'Config-dependent', 'Requires project/environment configuration before use.'],
          ['Resend', 'resend dependency in apps/web/package.json', 'Config-dependent', 'Used for email workflows where server/config is present.'],
          ['Express API server', 'express server scripts and /api proxy', 'Implemented', 'Local dev proxy configured in Vite.'],
        ],
      },
      { type: 'heading', id: 'dentalpilot-integrations', text: 'DentalPilot AI integrations' },
      {
        type: 'table',
        columns: ['Integration', 'Evidence', 'Status', 'Notes'],
        rows: [
          ['PostgreSQL', 'docker-compose local postgres service, SQLAlchemy/Alembic', 'Implemented', 'Primary local persistence for DentalPilot stack.'],
          ['Groq AI provider', 'Recent migration records and backend config', 'Implemented/config-dependent', 'Requires GROQ_API_KEY for live model calls.'],
          ['Docker Compose', 'docker-compose.local.yml', 'Implemented', 'Supported local development workflow.'],
        ],
      },
      { type: 'heading', id: 'planned-integrations', text: 'Planned integrations' },
      {
        type: 'callout',
        tone: 'planned',
        title: 'No unverified claims',
        text:
          'EHR/PMS/lab/payment integrations should only be documented as implemented when there is router, adapter, test, or deployment evidence. Otherwise list them as planned.',
      },
    ],
  },
  {
    id: 'security',
    slug: 'security',
    path: '/documentation/security',
    navLabel: 'Security & Governance',
    title: 'Security & Governance',
    description:
      'Security and governance practices that are implemented in code, and planned controls that must not be presented as certified or deployed without evidence.',
    updated: '2026-11-24',
    blocks: [
      {
        type: 'paragraph',
        text:
          'Security documentation must distinguish implemented controls from aspirational or planned controls. This page includes only repository-observable controls or explicitly labels planned items.',
      },
      { type: 'heading', id: 'implemented-controls', text: 'Implemented controls (repository-observable)' },
      {
        type: 'table',
        columns: ['Control', 'Evidence', 'Scope'],
        rows: [
          ['Helmet middleware dependency', 'apps/web/package.json includes helmet', 'Web server/security hardening capability; verify runtime wiring before claiming active.'],
          ['Input validation libraries', 'zod dependency in web app', 'Validation support in web codebase.'],
          ['DentalPilot auth/RBAC/rate-limit tests', 'DentalPilot audit records and backend tests', 'DentalPilot product scope.'],
          ['CSP/rate limiting/worker supervision work', 'DentalPilot remediation records', 'DentalPilot product scope; production behavior may differ.'],
        ],
      },
      { type: 'heading', id: 'governance-model', text: 'Governance model (planned UETI)' },
      {
        type: 'callout',
        tone: 'planned',
        title: 'Planned governance capabilities',
        text:
          'UETI policy/governance, evidence/verification, and accountability/audit are planned platform capabilities in website content. They should be described as target architecture, not active certifications or deployed platform services.',
      },
      { type: 'heading', id: 'security-reporting', text: 'Security reporting' },
      {
        type: 'paragraph',
        text:
          'For security questions, use the public contact route /contact or the documented security page /security. Do not publish secrets, credentials, or private customer data in documentation examples.',
      },
    ],
  },
  {
    id: 'troubleshooting',
    slug: 'troubleshooting',
    path: '/documentation/troubleshooting',
    navLabel: 'Operations & Troubleshooting',
    title: 'Operations & Troubleshooting',
    description:
      'Operational checks and troubleshooting guidance for the Otheryn website and known local development workflows.',
    updated: '2026-11-24',
    blocks: [
      {
        type: 'paragraph',
        text:
          'Use these checks for common local development and documentation navigation issues. Commands are scoped to the relevant app directory.',
      },
      { type: 'heading', id: 'web-app-troubleshooting', text: 'Website troubleshooting' },
      {
        type: 'table',
        columns: ['Symptom', 'Check', 'Action'],
        rows: [
          ['Website does not start', 'Run npm install in apps/web', 'Use npm run dev and check Vite output.'],
          ['/api calls fail locally', 'Check Vite proxy and server process', 'Run npm run dev:all or start server on port 3001.'],
          ['Documentation route 404 on refresh', 'Check deployment SPA rewrite rules', 'Configure host to serve index.html for /documentation/* routes.'],
          ['Footer documentation link incorrect', 'Inspect apps/web/src/data/index.ts', 'Resources -> Documentation should point to /documentation.'],
        ],
      },
      { type: 'heading', id: 'dentalpilot-troubleshooting', text: 'DentalPilot local troubleshooting' },
      {
        type: 'code',
        language: 'bash',
        label: 'DentalPilot local stack checks',
        code: `cd products/healthcare/dental/dentalpilot-ai
docker compose -f docker-compose.local.yml ps
docker compose -f docker-compose.local.yml logs --tail=50 backend frontend workers`,
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'Environment-specific behavior',
        text:
          'Docker, database credentials, ports, and external API keys can differ by machine. Validate against your local .env.local and running containers before changing code.',
      },
      { type: 'heading', id: 'documentation-validation', text: 'Documentation validation checklist' },
      {
        type: 'list',
        items: [
          'Direct URL access works for every /documentation route.',
          'Browser refresh works on deep documentation routes.',
          'Sidebar, search, breadcrumbs, TOC, prev/next, and copy buttons work on desktop and mobile.',
          'Documentation contains no unverified capability claims.',
        ],
      },
    ],
  },
  {
    id: 'changelog',
    slug: 'changelog',
    path: '/documentation/changelog',
    navLabel: 'Release Notes',
    title: 'Release Notes',
    description:
      'Release notes for documentation and publicly visible Otheryn website changes documented in this repository.',
    updated: '2026-11-24',
    blocks: [
      {
        type: 'paragraph',
        text:
          'Release notes track user-visible documentation and website changes. Product-specific release notes may also exist in product directories; this page focuses on Otheryn web/documentation changes.',
      },
      { type: 'heading', id: '2026-11-24', text: '2026-11-24 — Documentation Centre' },
      {
        type: 'list',
        items: [
          'Added dedicated Documentation Centre routes under /documentation with independent section routes.',
          'Implemented enterprise documentation layout with sidebar navigation, search, article content, right-side TOC, breadcrumbs, and previous/next navigation.',
          'Added copy-to-clipboard code blocks and responsive behavior for desktop, tablet, and mobile.',
          'Updated footer Resources -> Documentation to point to /documentation.',
          'Documented only repository-observable capabilities and labeled planned UETI capabilities explicitly.',
        ],
      },
      { type: 'heading', id: 'documentation-policy', text: 'Release note policy' },
      {
        type: 'callout',
        tone: 'info',
        title: 'Evidence-based entries',
        text:
          'Add release note entries only for merged/implemented changes. Avoid listing planned work as completed.',
      },
    ],
  },
];

export const DOC_NAV = [
  {
    title: 'Documentation',
    items: DOC_ARTICLES.map((article) => ({
      label: article.navLabel,
      path: article.path,
      slug: article.slug,
    })),
  },
];

export function getDocArticle(slug: string | undefined): DocArticle {
  return DOC_ARTICLES.find((article) => article.slug === slug) ?? DOC_ARTICLES[0];
}

export function getDocByPath(path: string): DocArticle | undefined {
  return DOC_ARTICLES.find((article) => article.path === path);
}

export function getAdjacentDocs(slug: string): { prev?: DocArticle; next?: DocArticle } {
  const index = DOC_ARTICLES.findIndex((article) => article.slug === slug);
  return {
    prev: index > 0 ? DOC_ARTICLES[index - 1] : undefined,
    next: index >= 0 && index < DOC_ARTICLES.length - 1 ? DOC_ARTICLES[index + 1] : undefined,
  };
}
