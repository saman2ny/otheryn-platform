# DentalPilot AI — Business Proposal

**Audience:** founders, investors, strategic partners, healthcare organizations, business stakeholders.
**Document type:** business strategy and product proposal. This is not a technical specification; see [`TECHNICAL_ARCHITECTURE.md`](TECHNICAL_ARCHITECTURE.md) for engineering detail and [`SETUP_AND_DEPLOYMENT.md`](SETUP_AND_DEPLOYMENT.md) for operations.

> **Evidence convention:** "Implemented" means present in the current repository. "Planned" means proposed and **not** implemented. Market sizes, pricing outcomes and financial results are **not** asserted; where numbers are needed they are marked as estimates or research requirements.

---

## 1. Executive Summary

DentalPilot AI is the first specialty product in the **Otheryn** healthcare intelligence and infrastructure ecosystem. It is an AI-assisted SaaS platform for dental clinics that digitizes the operational and growth work that usually happens between appointments: patient records, treatment coordination, billing, recall, communications, marketing content and reporting.

The current release (v1.2.0) is a working MVP covering dental practice workflows, a patient portal, clinic operations, growth/content tools and Razorpay billing. It is not a certified medical device, not a certified compliance product, and not a live PMS/EHR integration. See [`RELEASE_NOTES.md`](../../RELEASE_NOTES.md) for the exact release boundary.

The opportunity is to give dental practices one coherent, dental-specific system for the work that generic tools handle poorly or in isolation — while keeping clinical judgement with the clinician and keeping patient data private and auditable.

---

## 2. Company and Product Vision

**Vision:** a healthcare intelligence and infrastructure ecosystem in which specialty products share a common platform for identity, data governance, evidence, verification and AI-assisted workflows.

**DentalPilot AI's role:** the first specialty product proving the model in dentistry — combining practice operations, patient engagement, growth and billing in one product, with a path toward governed AI and connected care.

The vision includes capabilities that are **not implemented today** (governed execution, evidence/verification, AI agents, robotics interoperability). They are described as future direction only.

---

## 3. Mission and Objectives

**Mission:** reduce the administrative and growth burden on dental teams so clinicians can spend more time on care.

**Near-term objectives (implemented or in progress):**
- Provide a complete, usable dental practice workflow (patients, enquiries, visits, treatment plans, ledger, claims, records, consent, recall).
- Provide a patient portal for records, downloads and self-service treatment payments.
- Provide clinic operations tooling (digital dentistry cases, assets, maintenance, sterilisation logs, message/publication drafts, clinician note review).
- Provide growth/content tooling (AI-assisted marketing content, calendar, exports, local-listing audits, campaign/review drafts).
- Provide subscription and treatment-payment billing via Razorpay.
- Establish a secure, auditable, multi-tenant foundation.

**Longer-term objectives (planned):**
- Deeper interoperability (PMS, accounting, insurer/clearinghouse, device/robotics).
- Governed clinical AI (note drafting, image analysis) with clinical/privacy/regulatory assessment.
- Connected-care and referral workflows.
- A shared platform layer (identity, evidence, verification, audit) across future specialties.

---

## 4. Healthcare Industry Problem

Dental practices are small businesses with clinical, administrative and growth obligations. Common problems:

- **Fragmented tools:** practice management, billing, patient communication, marketing and reporting often live in separate systems.
- **Administrative load:** treatment coordination, recall, claims and record-keeping consume staff time.
- **Growth gap:** consistent, compliant, dental-specific marketing is hard to produce without an agency.
- **Patient experience:** patients expect digital access to records, reminders and payments.
- **Data silos:** limited interoperability between PMS, accounting, imaging and payment providers.
- **Governance:** sensitive health data requires strong access control, consent and audit.

These are qualitative, widely reported pain points. This document does **not** claim a specific market size; sizing is a research requirement (see §21).

---

## 5. Target Market and Customer Segments

| Segment | Description | Fit |
|---|---|---|
| Independent dental practices | 1–5 providers, owner-operated | Strong — replaces fragmented tools |
| Small dental groups | 2–10 locations, shared ops | Strong — organizations, branch scoping |
| Specialist practices | Orthodontics, oral surgery, periodontics, etc. | Medium — dental-specific workflows |
| DSOs / larger groups | Multi-clinic, reporting-heavy | Medium — organizations + aggregate reporting; needs deeper integrations |
| Patients | Individuals receiving care | Indirect — patient portal and payments |

**Geography:** initial focus is dental practices that can use the current currency/payment configuration (Razorpay, INR-primary; international payments may be required for non-INR). Geographic expansion is a go-to-market decision, not a claim.

---

## 6. Customer Pain Points

- No single place for patient records, treatment plans, ledger, claims and communications.
- Manual recall and follow-up; missed treatment opportunities.
- Content/marketing is inconsistent or outsourced.
- Billing and payment reconciliation is manual.
- Staff turnover and training across disconnected systems.
- Limited visibility into treatment performance, retention and revenue.
- Concern about data privacy and auditability.

---

## 7. Proposed Solution

DentalPilot AI provides one dental-specific workspace that connects:

1. **Practice operations** — patients, enquiries, visits, treatment plans/stages, ledger, insurance claims, records, consent, recall.
2. **Patient engagement** — patient portal, record access, expiring shares, self-service treatment payments.
3. **Clinic operations** — digital dentistry cases, assets/maintenance, sterilisation logs, message/publication drafts, clinician note review.
4. **Growth** — AI-assisted content, calendar, exports, local-listing audits, campaign/review drafts.
5. **Commerce** — subscription plans and Razorpay treatment payments.
6. **Governance** — audit events, consent, branch/clinic authorization, private file storage.

AI is an assistant, not a replacement for clinical judgement. Clinical notes are clinician-entered and require human review; AI note drafting is gated and not enabled by default.

---

## 8. Product Overview

| Area | Implemented in v1.2.0 | Planned |
|---|---|---|
| Practice workflows | ✅ | Deeper automation, PMS sync |
| Patient portal | ✅ | Richer self-service, messaging |
| Operations | ✅ | Device/robotics integration |
| Growth/content | ✅ | Automated SEO, review imports, publishing |
| Billing | ✅ (subscriptions + treatment payments) | Auto-reconciliation, refunds, terminals |
| AI | ✅ content generation; gated note drafting | Clinical AI, image analysis (governed) |
| Interoperability | CSV import/export; provider catalog | Vendor PMS, accounting, insurer integrations |
| Governance | ✅ audit, consent, S3 storage | Formal certifications, retention automation |

---

## 9. Core Product Modules

1. **Authentication & authorization** — JWT, roles, branch scoping.
2. **Clinic & organization management** — clinic profile, branches, staff invitations, organizations.
3. **Patient CRM & registration** — enquiries, conversion, patient records.
4. **Appointments & calendar** — visits, calendar events.
5. **Clinical records** — versioned records, revisions, file upload/download, consent.
6. **Treatment journey** — plans, stages, decisions, ledger, revenue recovery.
7. **Patient billing & payments** — treatment payment orders, Razorpay verification, patient portal checkout.
8. **Subscriptions** — Free/Starter/Professional/Enterprise, monthly/annual, invoices, webhooks.
9. **Financial reporting** — revenue, financial summary, treatment follow-up, retention, operational metrics, accounting CSV.
10. **Communications** — templates, outbox, email outbox, WhatsApp adapter.
11. **Document storage** — S3-compatible, presigned downloads, KMS.
12. **AI assistance** — marketing content, gated clinical note drafts.
13. **Growth & integrations** — local-listing audits, campaigns, review drafts, CSV import/export, provider catalog.
14. **Administration** — super-admin clinic listing (backend only).

---

## 10. Unique Value Proposition

- **Dental-specific**, not a generic AI writer or generic PMS add-on.
- **Integrated**: clinical, operational, growth and billing in one system.
- **Patient-facing**: portal, records, consent and self-service payments.
- **Governed**: audit, consent, private storage, branch/clinic scoping.
- **AI-assisted with human control**: clinician review, gated note drafting.
- **Composable**: independent products/versioning; shared platform direction.

---

## 11. Competitive Landscape

Categories (qualitative, not a ranked market study):

- **Practice management / EHR vendors** — strong clinical/PM functionality, weaker growth/marketing and patient-facing experience.
- **Dental marketing agencies/tools** — strong content, weak clinical/operational integration.
- **Generic AI writing tools** — not dental-specific, no clinical/PM context.
- **Point solutions** — recall, payments, imaging, etc., often disconnected.

A detailed competitor matrix requires primary research; this document does not assert market share or feature parity.

---

## 12. Competitor Comparison

| Capability | DentalPilot AI (implemented) | PMS/EHR | Marketing tools | Generic AI |
|---|---|---|---|---|
| Dental practice workflows | ✅ | ✅ | ❌ | ❌ |
| Patient portal & payments | ✅ | Partial | ❌ | ❌ |
| Treatment ledger & claims | ✅ | ✅ | ❌ | ❌ |
| AI marketing content | ✅ | ❌ | ✅ | ✅ |
| Clinical note drafting (gated) | ✅ (opt-in) | Partial | ❌ | ❌ |
| Audit/consent/private storage | ✅ | Partial | ❌ | ❌ |
| Vendor PMS integration | ❌ (CSV) | Native | ❌ | ❌ |

This is a qualitative comparison based on the current implementation, not a certified feature audit of competitors.

---

## 13. Differentiation and Competitive Advantages

- **One product, multiple workflows** — less context switching.
- **Dental-specific data model** — treatment stages, ledger, claims, recall.
- **Patient engagement built in** — portal, shares, self-service payments.
- **Governance by design** — audit, consent, branch scoping, private S3.
- **AI with boundaries** — human review, gated clinical drafting.
- **Composable platform** — independent products, shared direction.

---

## 14. Business Model

**Primary:** subscription SaaS with four tiers — **Free, Starter, Professional, Enterprise** — billed monthly or annually via Razorpay.

**Secondary (transactional):** patient treatment payments processed via Razorpay. These are patient charges, **not** subscription revenue.

**Not yet implemented:** usage-based AI metering/enforcement, partner/reseller billing, enterprise contracts. AI credit limits are tracked but not enforced (see technical debt).

Exact price points and plan IDs are configuration in the billing module and Razorpay; they are not asserted in this document.

---

## 15. Pricing and Revenue Streams

| Stream | Status | Notes |
|---|---|---|
| Subscription (Free/Starter/Professional/Enterprise) | Implemented | Monthly/annual via Razorpay; plan IDs configured |
| Treatment payments | Implemented | Patient-paid; separate from subscription |
| Usage-based AI | Planned | Credits tracked; enforcement not implemented |
| Partner/API revenue | Planned | No partner program yet |
| Enterprise services | Planned | No formal offering yet |

**Research requirement:** price elasticity, willingness-to-pay, competitive price benchmarks, and conversion assumptions must be validated with primary research before financial modelling.

---

## 16. Customer Acquisition Strategy

**Implemented/available today:**
- Direct sales to dental practices and groups.
- Product-led trial (Free tier).
- Content/SEO (marketing content features; external SEO automation is planned).
- Referral/word-of-mouth (no formal program).

**Planned:**
- Dental association/partner channels.
- PMS/accounting integration partnerships.
- Case studies and outcome-based marketing.
- Multi-location group sales.

No customer counts, CAC or conversion rates are asserted.

---

## 17. Market Expansion Strategy

1. **Deepen dentistry** — complete workflows, integrations, reporting.
2. **Expand specialties** — orthodontic, oral surgery, periodontics, etc.
3. **Geographic expansion** — payment/currency and compliance per market.
4. **Platform expansion** — shared identity/evidence/verification for future healthcare products.
5. **Ecosystem** — PMS, accounting, insurer, device/robotics integrations.

---

## 18. Product Roadmap

**Implemented (v1.2.0):** see [`RELEASE_NOTES.md`](../../RELEASE_NOTES.md).

**Next (planned):**
- Vendor PMS integrations and bidirectional sync (CSV is current).
- Accounting-provider integrations and automatic ledger posting.
- Insurer/clearinghouse claim submission and online refunds.
- Automated local SEO metrics, review imports, campaign attribution, external publishing.
- Email delivery for password resets and staff/patient invitations.
- AI-generated clinical notes/image analysis — only after clinical, privacy and regulatory assessment.
- Referral and connected-care workflows.
- Stronger production identity/session controls, credential rotation, tested backup/recovery, monitoring and incident response.

**Long-term (vision, not implemented):**
- Governed execution, evidence/verification, accountability/audit.
- AI agents and orchestration.
- IoT/robotics interoperability.

---

## 19. Operational Strategy

- **Product:** small, cross-functional teams per product; shared platform competencies (identity, data, infrastructure).
- **Delivery:** independent product releases; path-scoped CI; trunk-based development.
- **Quality:** automated tests, security scanning, code review, audit.
- **Support:** in-app guidance, documentation, direct support for early customers.
- **Compliance:** privacy-by-design, consent, audit; formal certifications are future work.

---

## 20. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Regulatory / health-data compliance | High | Privacy-by-design, consent, audit, legal review, certifications |
| Clinical safety / AI errors | High | Human review, gated AI, no autonomous clinical decisions |
| Security breach | High | Tenant isolation, S3 privacy, secrets management, scanning, incident response |
| PMS/interoperability complexity | Medium | CSV-first, provider-neutral adapters, phased integrations |
| Adoption / change management | Medium | Training, onboarding, clear UX, support |
| Payment/settlement issues | Medium | Signed webhooks, reconciliation, clear records |
| Key-person / operational | Medium | Documentation, backups, runbooks |
| Market/financial uncertainty | Medium | Research-driven pricing, staged investment |

---

## 21. Financial Assumptions and Business Economics

**No actual revenue, customer counts, CAC, LTV, churn or market size are asserted.** Any figures used for planning must be:

- Marked as **estimates** or **research requirements**.
- Derived from primary research (pricing, conversion, churn, market sizing).
- Validated against the implemented billing model (subscriptions + treatment payments).

**Illustrative economics to research (not claims):**
- Subscription tiers and price points.
- Gross margin (hosting, AI, storage, email, payments).
- CAC by channel; payback period.
- Churn and net revenue retention.
- Treatment-payment take rate (if any).
- AI usage cost per clinic.

---

## 22. Long-Term Growth Strategy

- **Land and expand:** single clinic → group → specialty → platform.
- **Integration moat:** PMS, accounting, insurer, device/robotics.
- **Data/evidence advantage:** governed, auditable clinical and operational data.
- **Platform reuse:** shared identity/evidence/verification across future healthcare products.
- **Ecosystem:** partners, marketplaces, referral networks.

---

## Appendix — Implemented vs planned (quick reference)

| Capability | Status |
|---|---|
| Dental practice workflows | Implemented |
| Patient portal + treatment payments | Implemented |
| Clinic operations (cases/assets/sterilisation/drafts) | Implemented |
| Growth/content + CSV exchange | Implemented |
| Subscription billing | Implemented |
| S3 storage / SMTP / WhatsApp adapter | Implemented |
| Vendor PMS / accounting / insurer integrations | Planned |
| Automated SEO/reviews/publishing | Planned |
| Clinical AI/image analysis | Planned (governed) |
| IoT/robotics | Planned (not implemented) |
| Governed execution/evidence/agents | Planned (not implemented) |

See [`TECHNICAL_ARCHITECTURE.md`](TECHNICAL_ARCHITECTURE.md) for engineering evidence and [`RELEASE_NOTES.md`](../../RELEASE_NOTES.md) for the release boundary.