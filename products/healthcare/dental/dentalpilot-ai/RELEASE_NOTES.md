# DentalPilot AI 1.2.0

Release date: 2026-11-20

## What is implemented in 1.2.0

### Dental practice workflows
- Branch-scoped clinic operations, staff invitations, and guided onboarding.
- Treatment plan lifecycle and patient decision history, including reasons, scheduling, and completion.
- Treatment ledger for charges, manual payments/refunds, and captured Razorpay or insurer remittances;
  revenue recovery separates estimates from collected amounts and outstanding balances and prevents
  mixed clinic currencies.
- Patient visit history and date-filtered clinic analytics for treatment performance, follow-up
  effectiveness, retention, scheduled/no-show visits, and open enquiries.
- Dental CRM enquiry pipeline, guarded status transitions, conversion to patient records, and
  communication history.
- Recall automation for post-treatment, deferred-treatment, and hygiene workflows, with configurable
  intervals and reminders held for staff approval and explicit email-consent confirmation.
- SMTP email outbox with retry handling for approved recall reminders and individual patient
  communications.
- Razorpay checkout for outstanding treatment charges, with server-calculated balances, payment
  verification, signed capture webhooks, and charge-linked ledger entries.
- Patient-portal self-service checkout for a patient's own outstanding treatment charges; online
  payment requires clinic-configured Razorpay credentials and currency.
- Manual insurance claim lifecycle and remittance tracking; payer remittances are recorded in the
  treatment ledger.
- Audited accounting CSV exports and provider-neutral PMS transaction CSV reconciliation with
  persisted run summaries and row-level results.
- Native case coordination for imaging, intraoral scans, labs, CAD/CAM, 3D printing, implants and
  robotics, plus manual asset maintenance and sterilisation-cycle logs.
- Patient communication drafts with channel-consent confirmation, manual publication planning, and
  clinician-entered note drafts with explicit review status.
- Optional clinic organizations with one-time invitations, aggregate operations reporting, and
  charge-ledger financial totals grouped by each clinic's native currency (without FX conversion).
  Organization owners manage roles and membership; admins can invite clinics; reporting-only members
  can view aggregate reports. Independent clinics remain independent unless they opt in.

### Patient passport, consent, and governance
- Versioned patient-record provenance and correction history.
- Optional private S3-compatible file uploads/downloads for validated PDF, JPEG, PNG, and WebP
  records, with clinic/branch authorization, server-side encryption, and audit events.
- Patient portal account activation, patient-owned record access, file download when a binary is
  stored, and expiring share links.
- Consent scope, recipient, expiry, revocation, and access history.
- Audit events for sensitive record access, edits, sharing, email approvals, imports, and exports.

### Clinic growth and integrations
- Provider-neutral patient CSV import/export with explicit field mapping, row-level errors, duplicate
  external-reference protection, and sync-job history.
- Manual Local SEO listing audits, campaign planning, and a review inbox with unpublished response
  drafts, plus manually managed publication drafts that are not posted to external platforms.
- A provider catalog and adapter boundary; only provider-neutral CSV is enabled for future
  interoperability. Catalog entries do not indicate live connections.
- Existing clinic analytics, billing, AI-credit usage, invoices, and content features.

## What remains for later releases

- Vendor-specific PMS integrations and bidirectional sync; CSV remains the current exchange.
- Accounting-provider integrations, automatic ledger posting, insurer/clearinghouse claim submission,
  online refunds, payment-terminal support, and payment-settlement reconciliation.
- Automated Local SEO metrics, external review imports, campaign attribution, and platform publishing.
- SMS/WhatsApp delivery and email delivery for password resets or staff/patient invitations.
- Actual DICOM viewers, scanner/lab/device connections, equipment telemetry, and robotics
  interoperability. Current case tracking and manual logs do not connect to hardware.
- AI-generated clinical notes or image analysis; current notes are clinician-entered and require
  human review. Validated clinical AI requires separate clinical, privacy, and regulatory assessment.
- Referral and connected-care workflows.
- Production identity/session controls, credential rotation, tested backup and recovery, operational
  monitoring, and incident-response procedures. Razorpay subscription webhooks and reconciliation are
  implemented but require the configured plan IDs, webhook secret, and a separately deployed worker service.
- Formal privacy, regulatory, clinical governance, and independent security assessments.

## Release boundary

Version 1.2.0 is an MVP workflow implementation. It does not claim medical-device approval,
regulatory certification, independent security certification, or live interoperability beyond the
configured Razorpay, S3-compatible storage, and SMTP paths. Provider credentials and production
settlement were not exercised in tests. Keep storage private, configure backups and retention, and use
synthetic or appropriately governed data until production identity, integration, and organizational
security controls have been reviewed.
