export type DentalCaseType =
  'imaging' | 'intraoral-scan' | 'lab' | 'cad-cam' | '3d-print' | 'implant' | 'robotics';

export type DentalCaseStatus =
  'requested' | 'planning' | 'in-progress' | 'awaiting-clinician' | 'completed' | 'cancelled';

export interface DentalWorkflowCase {
  id: string;
  branchId?: string;
  patientId: string;
  treatmentStageId?: string;
  caseType: DentalCaseType;
  title: string;
  status: DentalCaseStatus;
  providerName: string;
  externalReference: string;
  dueAt?: string;
  details: Record<string, unknown>;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface DentalWorkflowCaseCreate {
  branchId?: string;
  patientId: string;
  treatmentStageId?: string;
  caseType: DentalCaseType;
  title: string;
  providerName?: string;
  externalReference?: string;
  dueAt?: string;
  details?: Record<string, unknown>;
}

export interface DentalWorkflowEvent {
  id: string;
  caseId: string;
  eventType: 'milestone' | 'handoff' | 'approval' | 'note';
  title: string;
  notes: string;
  actorId: string;
  createdAt: string;
}

export type DentalAssetType =
  | 'dental-chair'
  | 'autoclave'
  | 'intraoral-scanner'
  | 'xray'
  | 'cbct'
  | '3d-printer'
  | 'surgical-robot'
  | 'other';

export type DentalAssetStatus = 'active' | 'service-due' | 'unavailable' | 'retired';

export interface ClinicAsset {
  id: string;
  branchId: string;
  assetTag: string;
  assetType: DentalAssetType;
  displayName: string;
  modelName: string;
  serialNumber: string;
  status: DentalAssetStatus;
  nextServiceAt?: string;
  notes: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface ClinicAssetCreate {
  branchId: string;
  assetTag: string;
  assetType: DentalAssetType;
  displayName: string;
  modelName?: string;
  serialNumber?: string;
  nextServiceAt?: string;
  notes?: string;
}

export interface AssetMaintenanceRecord {
  id: string;
  assetId: string;
  workType: 'maintenance' | 'breakdown' | 'repair' | 'calibration';
  status: 'planned' | 'in-progress' | 'completed' | 'cancelled';
  dueAt?: string;
  completedAt?: string;
  notes: string;
  createdBy: string;
  createdAt: string;
}

export interface SterilizationCycle {
  id: string;
  branchId: string;
  assetId: string;
  cycleReference: string;
  loadReference: string;
  result: 'passed' | 'failed' | 'needs-review';
  startedAt: string;
  completedAt?: string;
  operatorName: string;
  notes: string;
  recordedBy: string;
  createdAt: string;
}

export interface PatientMessageDraft {
  id: string;
  patientId: string;
  branchId?: string;
  channel: 'email' | 'sms' | 'whatsapp';
  subject: string;
  body: string;
  status: 'draft' | 'approved' | 'cancelled';
  consentConfirmed: boolean;
  createdBy: string;
  approvedBy?: string;
  approvedAt?: string;
  createdAt: string;
}

export interface MarketingPublicationDraft {
  id: string;
  branchId?: string;
  title: string;
  platform: 'google-business' | 'meta' | 'other';
  body: string;
  status: 'draft' | 'approved' | 'scheduled' | 'published' | 'cancelled';
  scheduledAt?: string;
  publishedAt?: string;
  createdBy: string;
  reviewedBy?: string;
  createdAt: string;
}

export interface ClinicalNoteDraft {
  id: string;
  patientId: string;
  visitId?: string;
  title: string;
  clinicianInput: string;
  draftText: string;
  generationSource: 'clinician' | 'xai';
  reviewStatus: 'pending-review' | 'approved' | 'rejected';
  createdBy: string;
  reviewedBy?: string;
  reviewedAt?: string;
  createdAt: string;
}

export interface ClinicalAiSettings {
  enabled: boolean;
  available: boolean;
}

export interface IntegrationCatalogEntry {
  providerId: string;
  name: string;
  integrationType: string;
  mode: string;
  enabled: boolean;
  futureCandidates: string[];
}

export interface ClinicOrganization {
  id: string;
  name: string;
  createdAt: string;
  clinicCount: number;
  currentMemberRole: OrganizationMemberRole;
}

export type OrganizationMemberRole =
  'organization-owner' | 'organization-admin' | 'reporting-only' | 'clinic-owner';

export type EditableOrganizationMemberRole = 'organization-admin' | 'reporting-only';

export interface OrganizationFinancialSummary {
  currency: string;
  clinicCount: number;
  chargesValue: number;
  paymentsReceived: number;
  refundsValue: number;
  netCollected: number;
  outstandingBalance: number;
}

export interface OrganizationAnalytics {
  organizationId: string;
  organizationName: string;
  clinicCount: number;
  branchCount: number;
  patientCount: number;
  openTreatmentStageCount: number;
  completedVisitCount: number;
  clinics: {
    clinicId: string;
    clinicName: string;
    branchCount: number;
    patientCount: number;
    financials: OrganizationFinancialSummary[];
  }[];
  financials: OrganizationFinancialSummary[];
}

export interface OrganizationMember {
  userId: string;
  clinicId: string;
  fullName: string;
  email: string;
  role: OrganizationMemberRole;
  createdAt: string;
}

export interface OrganizationInvitation {
  id: string;
  organizationId: string;
  email: string;
  invitationToken: string;
  expiresAt: string;
}
