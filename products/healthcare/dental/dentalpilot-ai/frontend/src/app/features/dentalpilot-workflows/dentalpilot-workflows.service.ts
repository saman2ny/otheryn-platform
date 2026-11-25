import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';
import {
  AuditEvent,
  AuditEventListResponse,
  AuditFilters,
  AuditSummary,
  ClinicBranch,
  ClinicPerformanceAnalytics,
  CommunicationOutbox,
  CommunicationOutboxCreate,
  CommunicationTemplate,
  CommunicationTemplateCreate,
  CommunicationTemplateUpdate,
  InsuranceClaim,
  InsuranceClaimCreate,
  InsuranceClaimUpdate,
  EmailOutbox,
  HealthRecord,
  HealthRecordRevision,
  IntegrationConnection,
  IntegrationSyncJob,
  OnboardingStatus,
  PatientVisitCreate,
  PatientVisit,
  PmsReconciliationResult,
  PmsReconciliationRow,
  PmsReconciliationRun,
  PatientCommunication,
  Patient,
  PatientCreate,
  PatientDuplicate,
  PatientEnquiry,
  PatientRevision,
  PatientEnquiryCreate,
  PatientPortalShare,
  RecallReminder,
  RecallAutomationSettings,
  RecordConsent,
  RevenueRecoverySummary,
  StaffInvitation,
  StaffMember,
  TreatmentDecision,
  TreatmentLedgerEntryCreate,
  TreatmentLedgerEntry,
  TreatmentPlan,
} from '../../core/models/healthcare.model';
import {
  TreatmentPaymentOrder,
  TreatmentPaymentOrderCreate,
  TreatmentPaymentVerify,
  VerifyPaymentRequest,
} from '../../core/models/billing.model';

@Injectable({ providedIn: 'root' })
export class DentalPilotWorkflowsService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  listPatients(q?: string, limit?: number, offset?: number): Observable<Patient[]> {
    let params = new HttpParams();
    if (q && q.trim()) {
      params = params.set('q', q.trim());
    }
    if (limit) {
      params = params.set('limit', String(limit));
    }
    if (offset) {
      params = params.set('offset', String(offset));
    }
    return this.http.get<Patient[]>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.patients}`, {
      params,
    });
  }

  getPatientRevisions(id: string): Observable<PatientRevision[]> {
    return this.http.get<PatientRevision[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.patients}/${id}/revisions`,
    );
  }

  createPatient(payload: PatientCreate): Observable<Patient> {
    return this.http.post<Patient>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.patients}`, payload);
  }

  getPatient(id: string): Observable<Patient> {
    return this.http.get<Patient>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.patients}/${id}`);
  }

  updatePatient(id: string, payload: Partial<Patient>): Observable<Patient> {
    return this.http.patch<Patient>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.patients}/${id}`,
      payload,
    );
  }

  findDuplicatePatients(email?: string, phone?: string): Observable<PatientDuplicate[]> {
    const params = new HttpParams().set('email', email ?? '').set('phone', phone ?? '');
    return this.http.get<PatientDuplicate[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.patients}/duplicates`,
      { params },
    );
  }

  listEnquiries(): Observable<PatientEnquiry[]> {
    return this.http.get<PatientEnquiry[]>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.enquiries}`);
  }

  createEnquiry(payload: PatientEnquiryCreate): Observable<PatientEnquiry> {
    return this.http.post<PatientEnquiry>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.enquiries}`,
      payload,
    );
  }

  updateEnquiryStatus(
    enquiryId: string,
    status: PatientEnquiry['status'],
  ): Observable<PatientEnquiry> {
    return this.http.patch<PatientEnquiry>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.enquiryById(enquiryId)}`,
      { status },
    );
  }

  convertEnquiry(enquiryId: string): Observable<PatientEnquiry> {
    return this.http.post<PatientEnquiry>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.convertEnquiry(enquiryId)}`,
      {},
    );
  }

  listCommunications(patientId: string): Observable<PatientCommunication[]> {
    return this.http.get<PatientCommunication[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.patientCommunications(patientId)}`,
    );
  }

  createCommunication(
    patientId: string,
    payload: Pick<PatientCommunication, 'channel' | 'direction' | 'summary'>,
  ): Observable<PatientCommunication> {
    return this.http.post<PatientCommunication>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.patientCommunications(patientId)}`,
      payload,
    );
  }

  listPlans(): Observable<TreatmentPlan[]> {
    return this.http.get<TreatmentPlan[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.treatmentPlans}`,
    );
  }

  listPatientDecisions(patientId: string): Observable<TreatmentDecision[]> {
    return this.http.get<TreatmentDecision[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.patientDecisions(patientId)}`,
    );
  }

  createPlan(payload: object): Observable<TreatmentPlan> {
    return this.http.post<TreatmentPlan>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.treatmentPlans}`,
      payload,
    );
  }

  updateStage(
    stageId: string,
    payload: { status: string; reason?: string; scheduledAt?: string },
  ): Observable<unknown> {
    return this.http.patch(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.updateStage(stageId)}`,
      payload,
    );
  }

  getRevenueRecovery(): Observable<RevenueRecoverySummary> {
    return this.http.get<RevenueRecoverySummary>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.revenueRecovery}`,
    );
  }

  listTreatmentLedger(): Observable<TreatmentLedgerEntry[]> {
    return this.http.get<TreatmentLedgerEntry[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.treatmentLedger}`,
    );
  }

  createLedgerEntry(payload: TreatmentLedgerEntryCreate): Observable<TreatmentLedgerEntry> {
    return this.http.post<TreatmentLedgerEntry>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.treatmentLedger}`,
      payload,
    );
  }

  createPatientPaymentOrder(
    payload: TreatmentPaymentOrderCreate,
  ): Observable<TreatmentPaymentOrder> {
    return this.http.post<TreatmentPaymentOrder>(
      `${this.baseUrl}/${API_ENDPOINTS.billing.patientPaymentOrder}`,
      payload,
    );
  }

  verifyPatientPayment(payload: VerifyPaymentRequest): Observable<TreatmentPaymentVerify> {
    return this.http.post<TreatmentPaymentVerify>(
      `${this.baseUrl}/${API_ENDPOINTS.billing.verifyPatientPayment}`,
      payload,
    );
  }

  downloadAccountingCsv(type: 'ledger' | 'claims'): Observable<Blob> {
    const endpoint =
      type === 'ledger'
        ? API_ENDPOINTS.billing.accountingLedgerCsv
        : API_ENDPOINTS.billing.accountingClaimsCsv;
    return this.http.get(`${this.baseUrl}/${endpoint}`, { responseType: 'blob' });
  }

  listInsuranceClaims(): Observable<InsuranceClaim[]> {
    return this.http.get<InsuranceClaim[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.insuranceClaims}`,
    );
  }

  createInsuranceClaim(payload: InsuranceClaimCreate): Observable<InsuranceClaim> {
    return this.http.post<InsuranceClaim>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.insuranceClaims}`,
      payload,
    );
  }

  updateInsuranceClaim(claimId: string, payload: InsuranceClaimUpdate): Observable<InsuranceClaim> {
    return this.http.patch<InsuranceClaim>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.insuranceClaimById(claimId)}`,
      payload,
    );
  }

  listPmsReconciliationRuns(): Observable<PmsReconciliationRun[]> {
    return this.http.get<PmsReconciliationRun[]>(
      `${this.baseUrl}/${API_ENDPOINTS.billing.pmsReconciliationRuns}`,
    );
  }

  listPmsReconciliationRows(runId: string): Observable<PmsReconciliationRow[]> {
    return this.http.get<PmsReconciliationRow[]>(
      `${this.baseUrl}/${API_ENDPOINTS.billing.pmsReconciliationRows(runId)}`,
    );
  }

  reconcilePmsCsv(
    file: File,
    mapping: Record<string, string>,
  ): Observable<PmsReconciliationResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('field_mapping', JSON.stringify(mapping));
    return this.http.post<PmsReconciliationResult>(
      `${this.baseUrl}/${API_ENDPOINTS.billing.reconcilePmsCsv}`,
      formData,
    );
  }

  getAnalytics(fromDate?: string, toDate?: string): Observable<ClinicPerformanceAnalytics> {
    let params = new HttpParams();
    if (fromDate) params = params.set('from_date', fromDate);
    if (toDate) params = params.set('to_date', toDate);
    return this.http.get<ClinicPerformanceAnalytics>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.analytics}`,
      { params },
    );
  }

  listVisits(): Observable<PatientVisit[]> {
    return this.http.get<PatientVisit[]>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.visits}`);
  }

  createVisit(payload: PatientVisitCreate): Observable<PatientVisit> {
    return this.http.post<PatientVisit>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.visits}`,
      payload,
    );
  }

  listBranches(): Observable<ClinicBranch[]> {
    return this.http.get<ClinicBranch[]>(`${this.baseUrl}/${API_ENDPOINTS.clinic.branches}`);
  }

  createBranch(payload: {
    name: string;
    address: string;
    phone: string;
  }): Observable<ClinicBranch> {
    return this.http.post<ClinicBranch>(
      `${this.baseUrl}/${API_ENDPOINTS.clinic.branches}`,
      payload,
    );
  }

  listStaff(): Observable<StaffMember[]> {
    return this.http.get<StaffMember[]>(`${this.baseUrl}/${API_ENDPOINTS.clinic.staff}`);
  }

  inviteStaff(payload: {
    email: string;
    fullName: string;
    branchId: string;
  }): Observable<StaffInvitation> {
    return this.http.post<StaffInvitation>(
      `${this.baseUrl}/${API_ENDPOINTS.clinic.staffInvitations}`,
      payload,
    );
  }

  getOnboarding(): Observable<OnboardingStatus> {
    return this.http.get<OnboardingStatus>(`${this.baseUrl}/${API_ENDPOINTS.clinic.onboarding}`);
  }

  completeOnboarding(): Observable<OnboardingStatus> {
    return this.http.post<OnboardingStatus>(
      `${this.baseUrl}/${API_ENDPOINTS.clinic.completeOnboarding}`,
      {},
    );
  }

  invitePatient(
    patientId: string,
  ): Observable<{ invitationToken: string; expiresAt: string; clinicId: string; email: string }> {
    return this.http.post<{
      invitationToken: string;
      expiresAt: string;
      clinicId: string;
      email: string;
    }>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.portalInvitations}`, { patientId });
  }

  listSyncJobs(): Observable<IntegrationSyncJob[]> {
    return this.http.get<IntegrationSyncJob[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.syncJobs}`,
    );
  }

  importCsv(file: File, mapping: Record<string, string>): Observable<IntegrationSyncJob> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('field_mapping', JSON.stringify(mapping));
    return this.http.post<IntegrationSyncJob>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.importCsv}`,
      formData,
    );
  }

  exportCsv(): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/${API_ENDPOINTS.healthcare.exportCsv}`, {
      responseType: 'blob',
    });
  }

  listRecords(): Observable<HealthRecord[]> {
    return this.http.get<HealthRecord[]>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.records}`);
  }

  correctRecord(
    recordId: string,
    payload: {
      title: string;
      sourceName: string;
      authorName: string;
      correctionReason: string;
    },
  ): Observable<HealthRecord> {
    return this.http.patch<HealthRecord>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.recordById(recordId)}`,
      payload,
    );
  }

  listRecordRevisions(recordId: string): Observable<HealthRecordRevision[]> {
    return this.http.get<HealthRecordRevision[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.recordRevisions(recordId)}`,
    );
  }

  listReminders(): Observable<RecallReminder[]> {
    return this.http.get<RecallReminder[]>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.reminders}`);
  }

  listAudit(filters: AuditFilters = {}): Observable<AuditEventListResponse> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params = params.set(key, String(value));
      }
    });
    return this.http.get<AuditEventListResponse>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.audit}`, { params });
  }

  getAuditSummary(filters: AuditFilters = {}): Observable<AuditSummary> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '' && key !== 'page' && key !== 'pageSize') {
        params = params.set(key, String(value));
      }
    });
    return this.http.get<AuditSummary>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.audit}/summary`, { params });
  }

  exportAuditCsv(filters: AuditFilters = {}): Observable<Blob> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '' && key !== 'page' && key !== 'pageSize') {
        params = params.set(key, String(value));
      }
    });
    return this.http.get(`${this.baseUrl}/${API_ENDPOINTS.healthcare.audit}/export`, {
      params,
      responseType: 'blob',
    });
  }

  listIntegrations(): Observable<IntegrationConnection[]> {
    return this.http.get<IntegrationConnection[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.integrations}`,
    );
  }

  createRecord(payload: object): Observable<HealthRecord> {
    return this.http.post<HealthRecord>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.records}`,
      payload,
    );
  }

  uploadRecordFile(recordId: string, file: File): Observable<HealthRecord> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<HealthRecord>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.uploadRecordFile(recordId)}`,
      formData,
    );
  }

  downloadRecordFile(recordId: string): Observable<Blob> {
    return this.http.get(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.downloadRecordFile(recordId)}`,
      { responseType: 'blob' },
    );
  }

  createConsent(payload: object): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/${API_ENDPOINTS.healthcare.consents}`, payload);
  }

  listConsents(): Observable<RecordConsent[]> {
    return this.http.get<RecordConsent[]>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.consents}`);
  }

  revokeConsent(consentId: string): Observable<unknown> {
    return this.http.post(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.revokeConsent(consentId)}`,
      {},
    );
  }

  createReminder(payload: object): Observable<RecallReminder> {
    return this.http.post<RecallReminder>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.reminders}`,
      payload,
    );
  }

  updateReminder(reminderId: string, reminderStatus: string): Observable<RecallReminder> {
    return this.http.patch<RecallReminder>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.reminderById(reminderId)}`,
      { status: reminderStatus },
    );
  }

  approveReminder(reminderId: string, consentConfirmed: boolean): Observable<RecallReminder> {
    return this.http.post<RecallReminder>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.approveReminder(reminderId)}`,
      { consentConfirmed },
    );
  }

  getRecallSettings(): Observable<RecallAutomationSettings> {
    return this.http.get<RecallAutomationSettings>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.recallSettings}`,
    );
  }

  saveRecallSettings(
    payload: Pick<
      RecallAutomationSettings,
      'postProcedureDays' | 'pendingTreatmentDays' | 'hygieneRecallDays'
    >,
  ): Observable<RecallAutomationSettings> {
    return this.http.put<RecallAutomationSettings>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.recallSettings}`,
      payload,
    );
  }

  listEmailOutbox(): Observable<EmailOutbox[]> {
    return this.http.get<EmailOutbox[]>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.emailOutbox}`);
  }

  sendPatientEmail(
    patientId: string,
    payload: { subject: string; bodyText: string; consentConfirmed: boolean },
  ): Observable<EmailOutbox> {
    return this.http.post<EmailOutbox>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.sendPatientEmail(patientId)}`,
      payload,
    );
  }

  createIntegration(payload: object): Observable<IntegrationConnection> {
    return this.http.post<IntegrationConnection>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.integrations}`,
      payload,
    );
  }

  // Communication Templates
  listCommunicationTemplates(channel?: string): Observable<CommunicationTemplate[]> {
    let params = new HttpParams();
    if (channel) params = params.set('channel', channel);
    return this.http.get<CommunicationTemplate[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.communicationTemplates}`,
      { params },
    );
  }

  createCommunicationTemplate(
    payload: CommunicationTemplateCreate,
  ): Observable<CommunicationTemplate> {
    return this.http.post<CommunicationTemplate>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.communicationTemplates}`,
      payload,
    );
  }

  updateCommunicationTemplate(
    templateId: string,
    payload: CommunicationTemplateUpdate,
  ): Observable<CommunicationTemplate> {
    return this.http.patch<CommunicationTemplate>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.communicationTemplateById(templateId)}`,
      payload,
    );
  }

  deleteCommunicationTemplate(templateId: string): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.communicationTemplateById(templateId)}`,
    );
  }

  // Communication Outbox
  sendCommunication(payload: CommunicationOutboxCreate): Observable<CommunicationOutbox> {
    return this.http.post<CommunicationOutbox>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.communicationOutbox}`,
      payload,
    );
  }

  listCommunicationOutbox(
    status?: string,
    patientId?: string,
    limit: number = 100,
  ): Observable<CommunicationOutbox[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    if (patientId) params = params.set('patient_id', patientId);
    params = params.set('limit', limit.toString());
    return this.http.get<CommunicationOutbox[]>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.communicationOutbox}`,
      { params },
    );
  }

  getCommunicationOutbox(outboxId: string): Observable<CommunicationOutbox> {
    return this.http.get<CommunicationOutbox>(
      `${this.baseUrl}/${API_ENDPOINTS.healthcare.communicationOutboxById(outboxId)}`,
    );
  }
}
