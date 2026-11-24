export interface MedicalHistory {
  conditions?: string[];
  allergies?: string[];
  medications?: string[];
  surgeries?: string[];
  notes?: string;
}

export interface DentalHistory {
  previousTreatments?: string[];
  conditions?: string[];
  procedures?: string[];
  concerns?: string;
}

export interface EmergencyContact {
  name: string;
  relationship?: string;
  phone: string;
}

export interface Patient {
  id: string;
  fullName: string;
  email?: string;
  phone?: string;
  dateOfBirth?: string;
  externalReference?: string;
  branchId?: string;
  consentChannel: 'email' | 'sms' | 'whatsapp' | 'phone';
  medicalHistory?: MedicalHistory | null;
  dentalHistory?: DentalHistory | null;
  emergencyContacts?: EmergencyContact[] | null;
  createdAt: string;
  updatedAt?: string | null;
  updatedAtBy?: string | null;
}

export interface PatientCreate {
  fullName: string;
  email?: string;
  phone?: string;
  dateOfBirth?: string;
  externalReference?: string;
  branchId?: string;
  consentChannel: 'email' | 'sms' | 'whatsapp' | 'phone';
  medicalHistory?: MedicalHistory | null;
  dentalHistory?: DentalHistory | null;
  emergencyContacts?: EmergencyContact[] | null;
}

export interface PatientDuplicate {
  id: string;
  fullName: string;
  email?: string | null;
  phone?: string | null;
  matchedOn: string;
}

export type PatientEnquiryStatus =
  'new' | 'contacted' | 'consultation-booked' | 'converted' | 'closed';

export interface PatientEnquiry {
  id: string;
  branchId: string;
  patientId?: string;
  fullName: string;
  email?: string;
  phone?: string;
  source: string;
  requestedService: string;
  notes: string;
  status: PatientEnquiryStatus;
  createdAt: string;
  updatedAt: string;
}

export interface PatientEnquiryCreate {
  fullName: string;
  email?: string;
  phone?: string;
  source: string;
  requestedService: string;
  notes: string;
}

export interface PatientCommunication {
  id: string;
  patientId: string;
  channel: 'email' | 'sms' | 'whatsapp' | 'phone' | 'in-person';
  direction: 'inbound' | 'outbound';
  summary: string;
  actorId: string;
  createdAt: string;
}

export interface TreatmentStage {
  id: string;
  name: string;
  description: string;
  status: 'recommended' | 'accepted' | 'deferred' | 'declined' | 'scheduled' | 'completed';
  estimatedValue: number;
  reason?: string;
  scheduledAt?: string;
  completedAt?: string;
  updatedBy: string;
  createdAt: string;
}

export interface TreatmentPlan {
  id: string;
  patientId: string;
  title: string;
  notes: string;
  clinicianName: string;
  status: string;
  estimatedValue: number;
  currency: string;
  stages: TreatmentStage[];
  createdAt: string;
  updatedAt: string;
}

export interface TreatmentDecision {
  id: string;
  patientId: string;
  stageId: string;
  decision: string;
  reason?: string;
  actorId: string;
  actorRole: string;
  createdAt: string;
}

export interface HealthRecord {
  id: string;
  patientId: string;
  recordType:
    'xray' | 'estimate' | 'prescription' | 'visit-summary' | 'lab-report' | 'image' | 'document';
  title: string;
  sourceName: string;
  authorName?: string;
  documentUrl?: string;
  originalFilename?: string;
  mimeType?: string;
  fileSizeBytes?: number;
  fileSha256?: string;
  metadataJson: Record<string, unknown>;
  provenanceHash: string;
  versionNumber: number;
  createdAt: string;
}

export interface HealthRecordRevision {
  id: string;
  recordId: string;
  revisionNumber: number;
  snapshot: Record<string, unknown>;
  correctionReason: string;
  actorId: string;
  createdAt: string;
}

export interface RevenueRecoverySummary {
  deferredValue: number;
  declinedValue: number;
  acceptedValue: number;
  completedValue: number;
  pendingStageCount: number;
  overdueStageCount: number;
  pendingValue: number;
  overdueValue: number;
  decisionCount: number;
  conversionRate: number;
  completionRate: number;
  currency: string;
  chargesValue: number;
  paymentsReceived: number;
  refundsValue: number;
  netCollected: number;
  outstandingBalance: number;
  ledgerEntryCount: number;
}

export interface ClinicPerformanceAnalytics {
  totalTreatmentStages: number;
  acceptedStages: number;
  completedStages: number;
  openFollowups: number;
  overdueFollowups: number;
  completedFollowups: number;
  workflowCompletionRate: number;
  followupCompletionRate: number;
  decisionCount: number;
  branchCount: number;
  completedVisits: number;
  uniquePatientsSeen: number;
  returningPatients: number;
  patientRetentionRate: number;
  noShowVisits: number;
  scheduledVisits: number;
  openEnquiries: number;
  pendingReminderApprovals: number;
  fromDate?: string;
  toDate?: string;
}

export interface ClinicBranch {
  id: string;
  clinicId: string;
  name: string;
  address: string;
  phone: string;
  isPrimary: boolean;
  createdAt: string;
}

export interface StaffMember {
  id: string;
  email: string;
  fullName: string;
  role: string;
  branchId?: string;
  createdAt: string;
}

export interface StaffInvitation {
  id: string;
  email: string;
  fullName: string;
  branchId: string;
  invitationToken: string;
  expiresAt: string;
}

export interface OnboardingStep {
  id: string;
  name: string;
  description: string;
  completed: boolean;
  required: boolean;
  order: number;
}

export interface OnboardingStatus {
  currentStep: number;
  totalSteps: number;
  steps: OnboardingStep[];
  profileComplete: boolean;
  branchCount: number;
  staffCount: number;
  subscriptionActive: boolean;
  onboardingCompletedAt?: string;
  canComplete: boolean;
}

export interface RecallReminder {
  id: string;
  patientId: string;
  reminderType: 'review' | 'hygiene' | 'post-procedure' | 'pending-visit';
  message: string;
  channel: 'email' | 'sms' | 'whatsapp' | 'phone';
  scheduledAt: string;
  status: 'pending-approval' | 'scheduled' | 'sent' | 'completed' | 'failed' | 'cancelled';
  consentConfirmed: boolean;
  consentConfirmedBy?: string;
  consentConfirmedAt?: string;
  createdAt: string;
}

export interface PatientVisit {
  id: string;
  patientId: string;
  branchId?: string;
  visitType: 'consultation' | 'treatment' | 'hygiene' | 'other';
  status: 'scheduled' | 'completed' | 'cancelled' | 'no-show';
  scheduledAt?: string;
  completedAt?: string;
  notes: string;
  actorId: string;
  createdAt: string;
}

export interface PatientVisitCreate {
  patientId: string;
  branchId?: string;
  visitType: PatientVisit['visitType'];
  status: PatientVisit['status'];
  scheduledAt?: string;
  completedAt?: string;
  notes?: string;
}

export interface TreatmentLedgerEntry {
  id: string;
  patientId: string;
  branchId?: string;
  stageId?: string;
  chargeEntryId?: string;
  entryType: 'charge' | 'payment' | 'refund';
  amount: number;
  currency: string;
  method: 'cash' | 'card' | 'bank-transfer' | 'insurance' | 'razorpay' | 'other';
  reference: string;
  notes: string;
  actorId: string;
  createdAt: string;
}

export interface TreatmentLedgerEntryCreate {
  patientId: string;
  branchId?: string;
  stageId?: string;
  chargeEntryId?: string;
  entryType: TreatmentLedgerEntry['entryType'];
  amount: number;
  currency: string;
  method: TreatmentLedgerEntry['method'];
  reference?: string;
  notes?: string;
}

export interface RecallAutomationSettings {
  postProcedureDays: number;
  pendingTreatmentDays: number;
  hygieneRecallDays: number;
  updatedAt: string;
}

export type InsuranceClaimStatus =
  | 'draft'
  | 'submitted'
  | 'in-review'
  | 'approved'
  | 'partially-approved'
  | 'partially-paid'
  | 'paid'
  | 'denied'
  | 'cancelled';

export interface InsuranceClaim {
  id: string;
  patientId: string;
  branchId?: string;
  chargeEntryId?: string;
  supportingRecordId?: string;
  payerName: string;
  claimNumber: string;
  status: InsuranceClaimStatus;
  billedAmount: number;
  approvedAmount?: number;
  paidAmount: number;
  currency: string;
  submittedAt?: string;
  resolvedAt?: string;
  denialReason: string;
  notes: string;
  actorId: string;
  createdAt: string;
  updatedAt: string;
}

export interface InsuranceClaimCreate {
  patientId: string;
  chargeEntryId?: string;
  supportingRecordId?: string;
  payerName: string;
  claimNumber?: string;
  billedAmount: number;
  currency: string;
  notes?: string;
}

export interface InsuranceClaimUpdate {
  status: InsuranceClaimStatus;
  approvedAmount?: number | null;
  paidAmount?: number;
  denialReason?: string;
  notes?: string;
}

export interface PmsReconciliationRun {
  id: string;
  filename: string;
  totalRows: number;
  matchedRows: number;
  mismatchRows: number;
  missingLocalRows: number;
  missingPmsRows: number;
  duplicateSourceRows: number;
  invalidRows: number;
  createdAt: string;
}

export interface PmsReconciliationRow {
  id: string;
  rowNumber?: number;
  status:
    | 'matched'
    | 'mismatch'
    | 'missing-local'
    | 'missing-pms'
    | 'duplicate-source'
    | 'duplicate-local'
    | 'invalid-source';
  transactionReference: string;
  patientReference: string;
  localLedgerEntryId?: string;
  entryType?: string;
  externalAmount?: number;
  localAmount?: number;
  currency: string;
  details: string;
}

export interface PmsReconciliationResult extends Omit<
  PmsReconciliationRun,
  'filename' | 'createdAt'
> {}

export interface EmailOutbox {
  id: string;
  status: 'pending' | 'sending' | 'sent' | 'failed';
  recipientEmail: string;
  subject: string;
  availableAt: string;
  sentAt?: string;
  attemptCount: number;
  lastError?: string;
  createdAt: string;
}

export interface CommunicationTemplate {
  id: string;
  clinicId: string;
  name: string;
  channel: 'email' | 'sms' | 'whatsapp' | 'push';
  subject?: string;
  bodyTemplate: string;
  variables: string[];
  isActive: boolean;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface CommunicationTemplateCreate {
  name: string;
  channel: 'email' | 'sms' | 'whatsapp' | 'push';
  subject?: string;
  bodyTemplate: string;
  variables?: string[];
}

export interface CommunicationTemplateUpdate {
  name?: string;
  channel?: 'email' | 'sms' | 'whatsapp' | 'push';
  subject?: string;
  bodyTemplate?: string;
  variables?: string[];
  isActive?: boolean;
}

export interface CommunicationOutbox {
  id: string;
  clinicId: string;
  patientId: string;
  channel: 'email' | 'sms' | 'whatsapp' | 'push';
  recipient: string;
  subject?: string;
  status: 'pending' | 'sending' | 'sent' | 'failed';
  attemptCount: number;
  maxAttempts: number;
  availableAt: string;
  sentAt?: string;
  lastError?: string;
  externalId?: string;
  createdBy: string;
  createdAt: string;
}

export interface CommunicationOutboxCreate {
  patientId: string;
  channel: 'email' | 'sms' | 'whatsapp' | 'push';
  recipient: string;
  subject?: string;
  body: string;
  templateId?: string;
}

export interface RecordConsent {
  id: string;
  patientId: string;
  purpose: string;
  recipientName: string;
  recordIds: string[];
  scope: ('view' | 'download' | 'share')[];
  expiresAt?: string;
  revokedAt?: string;
  createdAt: string;
}

export interface AuditEvent {
  id: string;
  actorId?: string;
  action: string;
  resourceType: string;
  resourceId?: string;
  detail: Record<string, unknown>;
  createdAt: string;
}

export interface IntegrationConnection {
  id: string;
  provider: string;
  integrationType: 'pms' | 'imaging' | 'payments' | 'communications';
  status: string;
  configurationJson: Record<string, unknown>;
  lastSyncedAt?: string;
  createdAt: string;
}

export interface IntegrationSyncJob {
  id: string;
  connectionId?: string;
  jobType: string;
  status: string;
  fieldMapping: Record<string, string>;
  processedCount: number;
  failedCount: number;
  errors: { row: number; message: string }[];
  startedAt?: string;
  completedAt?: string;
  createdAt: string;
}

export interface PatientPortalLogin {
  accessToken: string;
  tokenType: string;
  patient: Patient;
}

export interface PatientPortalShare {
  consentId: string;
  shareToken: string;
  expiresAt: string;
}

export interface PatientPortalSharedRecords {
  purpose: string;
  recipientName: string;
  records: HealthRecord[];
  expiresAt: string;
}
