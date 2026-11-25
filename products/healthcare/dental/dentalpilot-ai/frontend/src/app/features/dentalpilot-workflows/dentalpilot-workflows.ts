import { DatePipe, JsonPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin, of, switchMap } from 'rxjs';
import { NotificationService } from '../../core/services/notification.service';
import { AuthService } from '../../core/services/auth.service';
import { TreatmentPaymentOrder, VerifyPaymentRequest } from '../../core/models/billing.model';
import {
  AuditEvent,
  AuditEventListResponse,
  AuditFilters,
  AuditSummary,
  ClinicBranch,
  ClinicPerformanceAnalytics,
  InsuranceClaim,
  InsuranceClaimCreate,
  InsuranceClaimStatus,
  HealthRecord,
  HealthRecordRevision,
  IntegrationConnection,
  IntegrationSyncJob,
  EmailOutbox,
  OnboardingStatus,
  PatientCommunication,
  Patient,
  PatientDuplicate,
  PatientRevision,
  PatientVisit,
  PmsReconciliationRow,
  PmsReconciliationResult,
  PmsReconciliationRun,
  RecallAutomationSettings,
  RecallReminder,
  PatientEnquiry,
  PatientEnquiryCreate,
  RecordConsent,
  RevenueRecoverySummary,
  StaffInvitation,
  StaffMember,
  TreatmentDecision,
  TreatmentLedgerEntry,
  TreatmentPlan,
} from '../../core/models/healthcare.model';
import { PageHeader } from '../../shared/ui/page-header/page-header';
import { StatCard } from '../../shared/ui/stat-card/stat-card';
import { DentalPilotWorkflowsService } from './dentalpilot-workflows.service';

const WORKFLOW_TABS = [
  'overview',
  'journey',
  'revenue',
  'analytics',
  'passport',
  'consent',
  'governance',
  'reminders',
  'integrations',
  'clinic',
] as const;
type WorkflowTab = (typeof WORKFLOW_TABS)[number];

const isWorkflowTab = (value: string | null): value is WorkflowTab =>
  WORKFLOW_TABS.some((tab) => tab === value);

const WORKFLOW_TITLES: Record<WorkflowTab, string> = {
  overview: 'Patients & CRM',
  journey: 'Treatment journey',
  revenue: 'Revenue recovery',
  analytics: 'Dental analytics',
  passport: 'Patient passport',
  consent: 'Consent & audit',
  governance: 'Security & audit',
  reminders: 'Recall & follow-up',
  integrations: 'PMS integrations',
  clinic: 'Staff & branches',
};

interface InsuranceClaimEditForm {
  status: InsuranceClaimStatus;
  approvedAmount: number | null;
  paidAmount: number;
  denialReason: string;
  notes: string;
}

@Component({
  selector: 'dp-dentalpilot-workflows',
  imports: [FormsModule, DatePipe, JsonPipe, PageHeader, StatCard],
  templateUrl: './dentalpilot-workflows.html',
})
export class DentalPilotWorkflows {
  private readonly service = inject(DentalPilotWorkflowsService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  protected readonly auth = inject(AuthService);
  private readonly notifications = inject(NotificationService);

  protected readonly patients = signal<Patient[]>([]);
  protected readonly enquiries = signal<PatientEnquiry[]>([]);
  protected readonly communications = signal<PatientCommunication[]>([]);
  protected readonly selectedCrmPatientId = signal('');
  protected readonly plans = signal<TreatmentPlan[]>([]);
  protected readonly records = signal<HealthRecord[]>([]);
  protected readonly filteredRecords = computed(() => {
    const patientId = this.selectedCrmPatientId();
    if (!patientId) return this.records();
    return this.records().filter((record) => record.patientId === patientId);
  });
  protected readonly revisions = signal<HealthRecordRevision[]>([]);
  protected readonly revisionRecordId = signal('');
  protected readonly recordCorrectionId = signal('');
  protected readonly decisions = signal<TreatmentDecision[]>([]);
  protected readonly decisionPatientId = signal('');
  protected readonly reminders = signal<RecallReminder[]>([]);
  protected readonly pendingApprovalReminderId = signal('');
  protected readonly reminderConsentConfirmed = signal(false);
  protected readonly recallSettings = signal<RecallAutomationSettings | null>(null);
  protected readonly emailOutbox = signal<EmailOutbox[]>([]);
  protected readonly visits = signal<PatientVisit[]>([]);
  protected readonly ledgerEntries = signal<TreatmentLedgerEntry[]>([]);
  protected readonly insuranceClaims = signal<InsuranceClaim[]>([]);
  protected readonly pmsReconciliationRuns = signal<PmsReconciliationRun[]>([]);
  protected readonly pmsReconciliationRows = signal<PmsReconciliationRow[]>([]);
  protected readonly selectedPmsRunId = signal('');
  protected readonly audit = signal<AuditEvent[]>([]);
  protected readonly auditSummary = signal<AuditSummary | null>(null);
  protected readonly auditTotal = signal(0);
  protected readonly auditPage = signal(1);
  protected readonly auditPageSize = signal(25);
  protected readonly auditTotalPages = signal(1);
  protected readonly auditLoading = signal(false);
  protected readonly auditExporting = signal(false);
  protected readonly selectedAuditEvent = signal<AuditEvent | null>(null);
  protected readonly auditFilters = signal<AuditFilters>({
    q: '',
    action: '',
    resourceType: '',
    actorId: '',
    outcome: '',
    branchId: '',
    dateFrom: '',
    dateTo: '',
    eventId: '',
    ipAddress: '',
  });
  protected readonly auditAdvancedOpen = signal(false);
  protected readonly auditPageSizeOptions = [10, 25, 50, 100];
  protected readonly integrations = signal<IntegrationConnection[]>([]);
  protected readonly consents = signal<RecordConsent[]>([]);
  protected readonly recovery = signal<RevenueRecoverySummary | null>(null);
  protected readonly analytics = signal<ClinicPerformanceAnalytics | null>(null);
  protected readonly branches = signal<ClinicBranch[]>([]);
  protected readonly staff = signal<StaffMember[]>([]);
  protected readonly onboarding = signal<OnboardingStatus | null>(null);
  protected readonly syncJobs = signal<IntegrationSyncJob[]>([]);
  protected readonly staffInvitation = signal<StaffInvitation | null>(null);
  protected readonly portalInvitation = signal<{
    invitationToken: string;
    expiresAt: string;
    clinicId: string;
    email: string;
  } | null>(null);
  protected readonly selectedCsvFile = signal<File | null>(null);
  protected readonly selectedPmsCsvFile = signal<File | null>(null);
  protected readonly selectedRecordFile = signal<File | null>(null);
  protected readonly csvMappingText = signal('{"fullName":"fullName","email":"email"}');
  protected readonly pmsMappingText = signal(
    '{"transactionReference":"Transaction ID","patientReference":"Patient ID","entryType":"Type","amount":"Amount","currency":"Currency"}',
  );
  protected readonly exportingCsv = signal(false);
  protected readonly processingPmsCsv = signal(false);
  protected readonly creatingPaymentForCharge = signal('');
  protected readonly insuranceClaimEdits = new Map<string, InsuranceClaimEditForm>();
  protected readonly activeTab = signal<WorkflowTab>('overview');
  protected readonly pageTitle = computed(() => WORKFLOW_TITLES[this.activeTab()]);
  protected readonly saving = signal(false);
  protected readonly analyticsFromDate = signal('');
  protected readonly analyticsToDate = signal('');
  protected readonly patientForm = {
    fullName: '',
    email: '',
    phone: '',
    dateOfBirth: '',
    consentChannel: 'email' as 'email' | 'sms' | 'whatsapp' | 'phone',
  };
  protected readonly enquiryForm = {
    fullName: '',
    email: '',
    phone: '',
    source: 'phone',
    requestedService: '',
    notes: '',
  };
  protected readonly communicationForm = {
    channel: 'phone' as PatientCommunication['channel'],
    direction: 'outbound' as PatientCommunication['direction'],
    summary: '',
  };
  protected readonly patientEmailForm = {
    subject: '',
    bodyText: '',
    consentConfirmed: false,
  };
  protected readonly planForm = {
    patientId: '',
    title: '',
    notes: '',
    clinicianName: '',
    estimatedValue: 0,
    currency: 'INR',
    stageName: '',
    stageValue: 0,
  };
  protected readonly recordForm = {
    patientId: '',
    recordType: 'document' as
      'xray' | 'estimate' | 'prescription' | 'visit-summary' | 'lab-report' | 'image' | 'document',
    title: '',
    sourceName: '',
    authorName: '',
    documentUrl: '',
  };
  protected readonly ledgerForm = {
    patientId: '',
    stageId: '',
    chargeEntryId: '',
    entryType: 'payment' as 'charge' | 'payment' | 'refund',
    amount: 0,
    currency: 'INR',
    method: 'cash' as 'cash' | 'card' | 'bank-transfer' | 'insurance' | 'razorpay' | 'other',
    reference: '',
    notes: '',
  };
  protected readonly insuranceClaimForm = {
    patientId: '',
    chargeEntryId: '',
    supportingRecordId: '',
    payerName: '',
    claimNumber: '',
    billedAmount: 0,
    currency: 'INR',
    notes: '',
  };
  protected readonly visitForm = {
    patientId: '',
    visitType: 'hygiene' as 'consultation' | 'treatment' | 'hygiene' | 'other',
    status: 'completed' as 'scheduled' | 'completed' | 'cancelled' | 'no-show',
    visitAt: '',
    notes: '',
  };
  protected readonly recallSettingsForm = {
    postProcedureDays: 1,
    pendingTreatmentDays: 7,
    hygieneRecallDays: 180,
  };
  protected readonly recordCorrectionForm = {
    title: '',
    sourceName: '',
    authorName: '',
    correctionReason: '',
  };
  protected readonly consentForm = {
    patientId: '',
    purpose: '',
    recipientName: '',
    recordIdsText: '',
    scope: 'view' as 'view' | 'download' | 'share',
    expiresAt: '',
  };
  protected readonly decisionReason = signal('');
  protected readonly stageScheduledAt = signal('');
  protected readonly reminderForm = {
    patientId: '',
    reminderType: 'review' as 'review' | 'hygiene' | 'post-procedure' | 'pending-visit',
    message: '',
    channel: 'email' as 'email' | 'sms' | 'whatsapp' | 'phone',
    scheduledAt: '',
    consentConfirmed: false,
  };
  protected readonly integrationForm = {
    provider: '',
    integrationType: 'pms' as 'pms' | 'imaging' | 'payments' | 'communications',
  };
  protected readonly branchForm = { name: '', address: '', phone: '' };
  protected readonly staffForm = { fullName: '', email: '', branchId: '' };

  constructor() {
    this.route.queryParamMap.subscribe((params) => {
      const tab = params.get('tab');
      const nextTab = isWorkflowTab(tab) ? tab : 'overview';
      this.activeTab.set(nextTab);
      if (nextTab === 'governance') this.loadAudit(1);
    });
    this.load();
  }

  protected createPatient(): void {
    if (!this.patientForm.fullName.trim()) return;
    this.saving.set(true);
    this.service.createPatient({ ...this.patientForm }).subscribe({
      next: (patient) => {
        this.patients.update((items) => [patient, ...items]);
        this.patientForm.fullName = '';
        this.patientForm.email = '';
        this.patientForm.phone = '';
        this.patientForm.dateOfBirth = '';
        this.saving.set(false);
      },
      error: (error) => {
        this.saving.set(false);
        if (error?.status === 409) {
          this.notifications.error('A patient with this name and email already exists.');
        }
      },
    });
  }

  protected readonly editingPatientId = signal<string | null>(null);
  protected readonly duplicateMatches = signal<PatientDuplicate[]>([]);
  protected readonly editForm = {
    fullName: '',
    email: '',
    phone: '',
    dateOfBirth: '',
    consentChannel: 'email' as 'email' | 'sms' | 'whatsapp' | 'phone',
    medicalConditions: '',
    medicalAllergies: '',
    medicalMedications: '',
    medicalNotes: '',
    dentalTreatments: '',
    dentalConcerns: '',
    emergencyName: '',
    emergencyRelationship: '',
    emergencyPhone: '',
  };

  protected editPatient(patient: Patient): void {
    this.editingPatientId.set(patient.id);
    this.editForm.fullName = patient.fullName;
    this.editForm.email = patient.email ?? '';
    this.editForm.phone = patient.phone ?? '';
    this.editForm.dateOfBirth = patient.dateOfBirth ?? '';
    this.editForm.consentChannel = patient.consentChannel;
    const medical = patient.medicalHistory ?? {};
    this.editForm.medicalConditions = (medical.conditions ?? []).join(', ');
    this.editForm.medicalAllergies = (medical.allergies ?? []).join(', ');
    this.editForm.medicalMedications = (medical.medications ?? []).join(', ');
    this.editForm.medicalNotes = medical.notes ?? '';
    const dental = patient.dentalHistory ?? {};
    this.editForm.dentalTreatments = (dental.previousTreatments ?? []).join(', ');
    this.editForm.dentalConcerns = dental.concerns ?? '';
    const contact = patient.emergencyContacts?.[0];
    this.editForm.emergencyName = contact?.name ?? '';
    this.editForm.emergencyRelationship = contact?.relationship ?? '';
    this.editForm.emergencyPhone = contact?.phone ?? '';
  }

  protected cancelEdit(): void {
    this.editingPatientId.set(null);
    this.duplicateMatches.set([]);
  }

  protected savePatient(): void {
    const id = this.editingPatientId();
    if (!id) return;
    const payload: Partial<Patient> = {
      fullName: this.editForm.fullName.trim(),
      email: this.editForm.email.trim() || undefined,
      phone: this.editForm.phone.trim() || undefined,
      dateOfBirth: this.editForm.dateOfBirth || undefined,
      consentChannel: this.editForm.consentChannel,
      medicalHistory: {
        conditions: this.editForm.medicalConditions.split(',').map((v) => v.trim()).filter(Boolean),
        allergies: this.editForm.medicalAllergies.split(',').map((v) => v.trim()).filter(Boolean),
        medications: this.editForm.medicalMedications.split(',').map((v) => v.trim()).filter(Boolean),
        notes: this.editForm.medicalNotes.trim() || undefined,
      },
      dentalHistory: {
        previousTreatments: this.editForm.dentalTreatments
          .split(',')
          .map((v) => v.trim())
          .filter(Boolean),
        concerns: this.editForm.dentalConcerns.trim() || undefined,
      },
      emergencyContacts: this.editForm.emergencyName.trim()
        ? [
            {
              name: this.editForm.emergencyName.trim(),
              relationship: this.editForm.emergencyRelationship.trim(),
              phone: this.editForm.emergencyPhone.trim(),
            },
          ]
        : [],
    };
    this.service.updatePatient(id, payload).subscribe({
      next: (updated) => {
        this.patients.update((items) => items.map((p) => (p.id === updated.id ? updated : p)));
        this.notifications.success('Patient record updated.');
        this.cancelEdit();
      },
    });
  }

  protected checkDuplicates(): void {
    this.service.findDuplicatePatients(this.patientForm.email, this.patientForm.phone).subscribe({
      next: (matches) => this.duplicateMatches.set(matches),
    });
  }

  protected readonly patientRevisions = signal<PatientRevision[]>([]);
  protected readonly patientSearch = signal('');
  protected readonly patientLimit = signal(100);

  protected loadPatientRevisions(patient: Patient): void {
    this.service.getPatientRevisions(patient.id).subscribe({
      next: (items) => this.patientRevisions.set(items),
    });
  }

  protected searchPatients(): void {
    this.service.listPatients(this.patientSearch(), this.patientLimit()).subscribe({
      next: (items) => this.patients.set(items),
    });
  }

  protected loadMorePatients(): void {
    this.patientLimit.update((limit) => limit + 100);
    this.searchPatients();
  }

  protected createEnquiry(): void {
    const fullName = this.enquiryForm.fullName.trim();
    const email = this.enquiryForm.email.trim();
    const phone = this.enquiryForm.phone.trim();
    if (!fullName || (!email && !phone)) {
      this.notifications.error('Enter a patient name and at least one contact method.');
      return;
    }
    const payload: PatientEnquiryCreate = {
      fullName,
      ...(email ? { email } : {}),
      ...(phone ? { phone } : {}),
      source: this.enquiryForm.source,
      requestedService: this.enquiryForm.requestedService.trim(),
      notes: this.enquiryForm.notes.trim(),
    };
    this.service.createEnquiry(payload).subscribe({
      next: (enquiry) => {
        this.enquiries.update((items) => [enquiry, ...items]);
        this.enquiryForm.fullName = '';
        this.enquiryForm.email = '';
        this.enquiryForm.phone = '';
        this.enquiryForm.requestedService = '';
        this.enquiryForm.notes = '';
        this.notifications.success('Patient enquiry added to the CRM.');
      },
    });
  }

  protected updateEnquiryStatus(enquiryId: string, status: PatientEnquiry['status']): void {
    this.service.updateEnquiryStatus(enquiryId, status).subscribe({
      next: (updated) => {
        this.enquiries.update((items) =>
          items.map((item) => (item.id === updated.id ? updated : item)),
        );
        this.notifications.success('Enquiry status updated.');
      },
    });
  }

  protected convertEnquiry(enquiryId: string): void {
    this.service.convertEnquiry(enquiryId).subscribe({
      next: (updated) => {
        this.enquiries.update((items) =>
          items.map((item) => (item.id === updated.id ? updated : item)),
        );
        this.notifications.success('Enquiry converted to a patient record.');
        this.load();
      },
    });
  }

  protected loadPatientCommunications(patientId: string): void {
    this.selectedCrmPatientId.set(patientId);
    if (!patientId) {
      this.communications.set([]);
      return;
    }
    this.service.listCommunications(patientId).subscribe((items) => this.communications.set(items));
  }

  protected createCommunication(): void {
    const patientId = this.selectedCrmPatientId();
    const summary = this.communicationForm.summary.trim();
    if (!patientId || summary.length < 3) {
      this.notifications.error('Select a patient and enter a communication summary.');
      return;
    }
    this.service.createCommunication(patientId, { ...this.communicationForm, summary }).subscribe({
      next: (communication) => {
        this.communications.update((items) => [communication, ...items]);
        this.communicationForm.summary = '';
        this.notifications.success('Communication added to the patient history.');
      },
    });
  }

  protected sendPatientEmail(): void {
    const patientId = this.selectedCrmPatientId();
    if (!patientId || !this.patientEmailForm.consentConfirmed) {
      this.notifications.error('Select a patient and confirm email consent before sending.');
      return;
    }
    this.service.sendPatientEmail(patientId, { ...this.patientEmailForm }).subscribe({
      next: (outboxItem) => {
        this.emailOutbox.update((items) => [outboxItem, ...items]);
        this.patientEmailForm.subject = '';
        this.patientEmailForm.bodyText = '';
        this.patientEmailForm.consentConfirmed = false;
        this.notifications.success('Email queued for delivery.');
      },
    });
  }

  protected createPlan(): void {
    if (!this.planForm.patientId || !this.planForm.title || !this.planForm.clinicianName) return;
    this.saving.set(true);
    const stage = this.planForm.stageName
      ? [
          {
            name: this.planForm.stageName,
            estimatedValue: this.planForm.stageValue,
            status: 'recommended',
          },
        ]
      : [];
    this.service
      .createPlan({
        patientId: this.planForm.patientId,
        title: this.planForm.title,
        notes: this.planForm.notes,
        clinicianName: this.planForm.clinicianName,
        estimatedValue: this.planForm.estimatedValue,
        currency: this.planForm.currency,
        stages: stage,
      })
      .subscribe({
        next: (plan) => {
          this.plans.update((items) => [plan, ...items]);
          this.planForm.title = '';
          this.planForm.notes = '';
          this.planForm.stageName = '';
          this.planForm.estimatedValue = 0;
          this.planForm.stageValue = 0;
          this.saving.set(false);
          this.load();
        },
        error: () => this.saving.set(false),
      });
  }

  protected updateStage(stageId: string, status: string): void {
    const reason = this.decisionReason().trim();
    if ((status === 'deferred' || status === 'declined') && !reason) {
      this.notifications.error('Enter a reason before deferring or declining treatment.');
      return;
    }
    const scheduledAt = this.stageScheduledAt();
    if (status === 'scheduled' && !scheduledAt) {
      this.notifications.error('Choose an appointment time before scheduling treatment.');
      return;
    }
    this.service
      .updateStage(stageId, {
        status,
        ...(reason ? { reason } : {}),
        ...(status === 'scheduled' ? { scheduledAt: new Date(scheduledAt).toISOString() } : {}),
      })
      .subscribe({
        next: () => {
          if (status === 'deferred' || status === 'declined') this.decisionReason.set('');
          if (status === 'scheduled') this.stageScheduledAt.set('');
          this.load();
          if (this.decisionPatientId()) this.loadPatientDecisions(this.decisionPatientId());
        },
      });
  }

  protected loadPatientDecisions(patientId: string): void {
    this.decisionPatientId.set(patientId);
    if (!patientId) {
      this.decisions.set([]);
      return;
    }
    this.service
      .listPatientDecisions(patientId)
      .subscribe((decisions) => this.decisions.set(decisions));
  }

  protected createRecord(): void {
    if (!this.recordForm.patientId || !this.recordForm.title || !this.recordForm.sourceName) return;
    this.saving.set(true);
    const selectedFile = this.selectedRecordFile();
    this.service
      .createRecord({
        ...this.recordForm,
        metadataJson: { createdIn: 'DentalPilot UI' },
      })
      .pipe(
        switchMap((record) =>
          selectedFile ? this.service.uploadRecordFile(record.id, selectedFile) : of(record),
        ),
      )
      .subscribe({
        next: (record) => {
          this.records.update((items) => [record, ...items]);
          this.recordForm.title = '';
          this.recordForm.sourceName = '';
          this.recordForm.documentUrl = '';
          this.selectedRecordFile.set(null);
          this.saving.set(false);
        },
        error: () => this.saving.set(false),
      });
  }

  protected onRecordFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedRecordFile.set(input.files?.[0] ?? null);
  }

  protected downloadRecordFile(record: HealthRecord): void {
    this.service.downloadRecordFile(record.id).subscribe({
      next: (file) => {
        const url = URL.createObjectURL(file);
        const link = document.createElement('a');
        link.href = url;
        link.download = record.originalFilename || `${record.title}.bin`;
        link.click();
        URL.revokeObjectURL(url);
      },
    });
  }

  protected toggleRecordRevisions(recordId: string): void {
    if (this.revisionRecordId() === recordId) {
      this.revisionRecordId.set('');
      this.revisions.set([]);
      return;
    }
    this.revisionRecordId.set(recordId);
    this.service
      .listRecordRevisions(recordId)
      .subscribe((revisions) => this.revisions.set(revisions));
  }

  protected openRecordCorrection(record: HealthRecord): void {
    this.recordCorrectionId.set(record.id);
    this.recordCorrectionForm.title = record.title;
    this.recordCorrectionForm.sourceName = record.sourceName;
    this.recordCorrectionForm.authorName = record.authorName ?? '';
    this.recordCorrectionForm.correctionReason = '';
  }

  protected correctRecord(): void {
    const recordId = this.recordCorrectionId();
    if (!recordId || this.recordCorrectionForm.correctionReason.trim().length < 5) {
      this.notifications.error('Enter a correction reason of at least five characters.');
      return;
    }
    this.service.correctRecord(recordId, { ...this.recordCorrectionForm }).subscribe({
      next: (record) => {
        this.records.update((items) =>
          items.map((item) => (item.id === record.id ? record : item)),
        );
        this.recordCorrectionId.set('');
        this.notifications.success('Record correction saved with provenance history.');
        this.revisionRecordId.set(record.id);
        this.service
          .listRecordRevisions(record.id)
          .subscribe((revisions) => this.revisions.set(revisions));
      },
    });
  }

  protected updateReminder(reminderId: string, reminderStatus: string): void {
    this.service.updateReminder(reminderId, reminderStatus).subscribe({
      next: (updated) => {
        this.reminders.update((items) =>
          items.map((reminder) => (reminder.id === updated.id ? updated : reminder)),
        );
        this.notifications.success(`Reminder marked ${reminderStatus}.`);
      },
    });
  }

  protected createConsent(): void {
    const recordIds = this.consentForm.recordIdsText
      .split(',')
      .map((id) => id.trim())
      .filter(Boolean);
    if (!this.consentForm.patientId || !this.consentForm.purpose || !recordIds.length) return;
    this.service
      .createConsent({
        patientId: this.consentForm.patientId,
        purpose: this.consentForm.purpose,
        recipientName: this.consentForm.recipientName,
        recordIds,
        scope: [this.consentForm.scope],
        ...(this.consentForm.expiresAt
          ? { expiresAt: new Date(this.consentForm.expiresAt).toISOString() }
          : {}),
      })
      .subscribe({
        next: () => {
          this.consentForm.recordIdsText = '';
          this.notifications.success('Record-sharing consent saved.');
          this.load();
        },
      });
  }

  protected revokeConsent(consentId: string): void {
    this.service.revokeConsent(consentId).subscribe({ next: () => this.load() });
  }

  protected beginReminderApproval(reminderId: string): void {
    this.pendingApprovalReminderId.set(reminderId);
    this.reminderConsentConfirmed.set(false);
  }

  protected approveReminder(): void {
    const reminderId = this.pendingApprovalReminderId();
    if (!reminderId || !this.reminderConsentConfirmed()) {
      this.notifications.error('Confirm the patient’s email consent before approval.');
      return;
    }
    this.service.approveReminder(reminderId, true).subscribe({
      next: (updated) => {
        this.reminders.update((items) =>
          items.map((item) => (item.id === updated.id ? updated : item)),
        );
        this.pendingApprovalReminderId.set('');
        this.reminderConsentConfirmed.set(false);
        this.notifications.success('Reminder approved and queued for its scheduled time.');
        this.loadOutbox();
      },
    });
  }

  protected saveRecallSettings(): void {
    this.service.saveRecallSettings(this.recallSettingsForm).subscribe({
      next: (settings) => {
        this.recallSettings.set(settings);
        this.notifications.success('Recall automation settings saved.');
      },
    });
  }

  protected loadOutbox(): void {
    this.service.listEmailOutbox().subscribe({
      next: (items) => this.emailOutbox.set(items),
    });
  }

  protected createReminder(): void {
    if (
      !this.reminderForm.patientId ||
      !this.reminderForm.message ||
      !this.reminderForm.scheduledAt ||
      !this.reminderForm.consentConfirmed
    )
      return;
    this.service
      .createReminder({
        ...this.reminderForm,
        scheduledAt: new Date(this.reminderForm.scheduledAt).toISOString(),
      })
      .subscribe({
        next: (reminder) => {
          this.reminders.update((items) => [reminder, ...items]);
          this.reminderForm.message = '';
          this.reminderForm.scheduledAt = '';
          this.reminderForm.consentConfirmed = false;
        },
      });
  }

  protected createLedgerEntry(): void {
    if (!this.ledgerForm.patientId || this.ledgerForm.amount <= 0) {
      this.notifications.error('Select a patient and enter an amount greater than zero.');
      return;
    }
    const { stageId, chargeEntryId, ...entry } = this.ledgerForm;
    this.service
      .createLedgerEntry({
        ...entry,
        ...(stageId ? { stageId } : {}),
        ...(chargeEntryId && this.ledgerForm.entryType !== 'charge' ? { chargeEntryId } : {}),
        reference: this.ledgerForm.reference.trim(),
        notes: this.ledgerForm.notes.trim(),
      })
      .subscribe({
        next: (entry) => {
          this.ledgerEntries.update((items) => [entry, ...items]);
          this.ledgerForm.amount = 0;
          this.ledgerForm.stageId = '';
          this.ledgerForm.chargeEntryId = '';
          this.ledgerForm.reference = '';
          this.ledgerForm.notes = '';
          this.notifications.success('Treatment ledger entry recorded.');
          this.load();
        },
      });
  }

  protected availableLedgerStages() {
    return this.plans()
      .filter((plan) => plan.patientId === this.ledgerForm.patientId)
      .flatMap((plan) => plan.stages.map((stage) => ({ ...stage, currency: plan.currency })));
  }

  protected updateLedgerPatient(patientId: string): void {
    this.ledgerForm.patientId = patientId;
    this.ledgerForm.stageId = '';
    this.ledgerForm.chargeEntryId = '';
  }

  protected availableLedgerCharges(): TreatmentLedgerEntry[] {
    return this.ledgerEntries().filter(
      (entry) => entry.patientId === this.ledgerForm.patientId && entry.entryType === 'charge',
    );
  }

  protected updateLedgerCharge(chargeEntryId: string): void {
    this.ledgerForm.chargeEntryId = chargeEntryId;
    const charge = this.ledgerEntries().find((entry) => entry.id === chargeEntryId);
    if (charge) {
      this.ledgerForm.currency = charge.currency;
      this.ledgerForm.stageId = charge.stageId ?? '';
    }
  }

  protected updateLedgerEntryType(entryType: 'charge' | 'payment' | 'refund'): void {
    this.ledgerForm.entryType = entryType;
    if (entryType === 'charge') this.ledgerForm.chargeEntryId = '';
  }

  protected chargeBalance(charge: TreatmentLedgerEntry): number {
    const entries = this.ledgerEntries().filter((entry) => entry.chargeEntryId === charge.id);
    const paid = entries
      .filter((entry) => entry.entryType === 'payment')
      .reduce((total, entry) => total + entry.amount, 0);
    const refunded = entries
      .filter((entry) => entry.entryType === 'refund')
      .reduce((total, entry) => total + entry.amount, 0);
    return Math.max(0, charge.amount - paid + refunded);
  }

  protected patientName(patientId: string): string {
    return (
      this.patients().find((patient) => patient.id === patientId)?.fullName ?? 'Unknown patient'
    );
  }

  protected startPatientPayment(charge: TreatmentLedgerEntry): void {
    this.creatingPaymentForCharge.set(charge.id);
    this.service.createPatientPaymentOrder({ chargeEntryId: charge.id }).subscribe({
      next: (order) => this.openTreatmentPaymentCheckout(order),
      error: () => {
        this.creatingPaymentForCharge.set('');
        this.notifications.error(
          'Unable to start treatment payment. Check the balance and try again.',
        );
      },
    });
  }

  private openTreatmentPaymentCheckout(order: TreatmentPaymentOrder): void {
    const user = this.auth.currentUser();
    const checkout = new Razorpay({
      key: order.keyId,
      amount: order.amount,
      currency: order.currency,
      name: 'DentalPilot AI',
      description: 'Dental treatment payment',
      order_id: order.orderId,
      prefill: { name: user?.fullName, email: user?.email },
      theme: { color: '#0f766e' },
      handler: (response) => {
        const verification: VerifyPaymentRequest = {
          razorpayOrderId: response.razorpay_order_id,
          razorpayPaymentId: response.razorpay_payment_id,
          razorpaySignature: response.razorpay_signature,
        };
        this.service.verifyPatientPayment(verification).subscribe({
          next: () => {
            this.creatingPaymentForCharge.set('');
            this.notifications.success('Treatment payment captured and recorded.');
            this.load();
          },
          error: () => {
            this.creatingPaymentForCharge.set('');
            this.notifications.error(
              'Payment verification is pending. Do not retry if you were charged; ask the clinic to reconcile the payment.',
            );
          },
        });
      },
      modal: { ondismiss: () => this.creatingPaymentForCharge.set('') },
    });
    checkout.on('payment.failed', (failure) => {
      this.creatingPaymentForCharge.set('');
      this.notifications.error(failure.error.description || 'Treatment payment failed.');
    });
    checkout.open();
  }

  protected downloadAccountingCsv(type: 'ledger' | 'claims'): void {
    this.service.downloadAccountingCsv(type).subscribe({
      next: (file) => {
        const url = URL.createObjectURL(file);
        const link = document.createElement('a');
        link.href = url;
        link.download =
          type === 'ledger'
            ? 'dentalpilot-accounting-ledger.csv'
            : 'dentalpilot-insurance-claims.csv';
        link.click();
        URL.revokeObjectURL(url);
        this.notifications.success('Accounting CSV downloaded.');
      },
    });
  }

  protected createInsuranceClaim(): void {
    if (!this.insuranceClaimForm.patientId || !this.insuranceClaimForm.payerName.trim()) {
      this.notifications.error('Select a patient and enter an insurance payer.');
      return;
    }
    const payload: InsuranceClaimCreate = {
      patientId: this.insuranceClaimForm.patientId,
      payerName: this.insuranceClaimForm.payerName.trim(),
      claimNumber: this.insuranceClaimForm.claimNumber.trim(),
      billedAmount: this.insuranceClaimForm.billedAmount,
      currency: this.insuranceClaimForm.currency,
      notes: this.insuranceClaimForm.notes.trim(),
      ...(this.insuranceClaimForm.chargeEntryId
        ? { chargeEntryId: this.insuranceClaimForm.chargeEntryId }
        : {}),
      ...(this.insuranceClaimForm.supportingRecordId
        ? { supportingRecordId: this.insuranceClaimForm.supportingRecordId }
        : {}),
    };
    this.service.createInsuranceClaim(payload).subscribe({
      next: (claim) => {
        this.insuranceClaims.update((claims) => [claim, ...claims]);
        this.insuranceClaimForm.claimNumber = '';
        this.insuranceClaimForm.billedAmount = 0;
        this.insuranceClaimForm.notes = '';
        this.notifications.success('Insurance claim added to the manual tracking queue.');
      },
    });
  }

  protected updateInsuranceClaimPatient(patientId: string): void {
    this.insuranceClaimForm.patientId = patientId;
    this.insuranceClaimForm.chargeEntryId = '';
    this.insuranceClaimForm.supportingRecordId = '';
  }

  protected availableClaimCharges(): TreatmentLedgerEntry[] {
    return this.ledgerEntries().filter(
      (entry) =>
        entry.patientId === this.insuranceClaimForm.patientId && entry.entryType === 'charge',
    );
  }

  protected updateInsuranceClaimCharge(chargeEntryId: string): void {
    this.insuranceClaimForm.chargeEntryId = chargeEntryId;
    const charge = this.ledgerEntries().find((entry) => entry.id === chargeEntryId);
    if (charge) {
      this.insuranceClaimForm.currency = charge.currency;
      this.insuranceClaimForm.billedAmount = charge.amount;
    }
  }

  protected availableClaimRecords(): HealthRecord[] {
    return this.records().filter(
      (record) => record.patientId === this.insuranceClaimForm.patientId,
    );
  }

  protected insuranceClaimEdit(claim: InsuranceClaim): InsuranceClaimEditForm {
    let edit = this.insuranceClaimEdits.get(claim.id);
    if (!edit) {
      edit = {
        status: claim.status,
        approvedAmount: claim.approvedAmount ?? null,
        paidAmount: claim.paidAmount,
        denialReason: claim.denialReason,
        notes: claim.notes,
      };
      this.insuranceClaimEdits.set(claim.id, edit);
    }
    return edit;
  }

  protected updateInsuranceClaimStatus(claim: InsuranceClaim, status: InsuranceClaimStatus): void {
    this.insuranceClaimEdit(claim).status = status;
  }

  protected updateInsuranceClaimApprovedAmount(
    claim: InsuranceClaim,
    approvedAmount: number | null,
  ): void {
    this.insuranceClaimEdit(claim).approvedAmount = approvedAmount;
  }

  protected updateInsuranceClaimPaidAmount(claim: InsuranceClaim, paidAmount: number): void {
    this.insuranceClaimEdit(claim).paidAmount = paidAmount;
  }

  protected updateInsuranceClaimDenialReason(claim: InsuranceClaim, denialReason: string): void {
    this.insuranceClaimEdit(claim).denialReason = denialReason;
  }

  protected updateInsuranceClaimNotes(claim: InsuranceClaim, notes: string): void {
    this.insuranceClaimEdit(claim).notes = notes;
  }

  protected insuranceClaimStatusOptions(claim: InsuranceClaim): InsuranceClaimStatus[] {
    const transitions: Record<InsuranceClaimStatus, InsuranceClaimStatus[]> = {
      draft: ['submitted', 'cancelled'],
      submitted: ['in-review', 'approved', 'partially-approved', 'denied', 'cancelled'],
      'in-review': ['approved', 'partially-approved', 'denied', 'cancelled'],
      approved: ['partially-paid', 'paid', 'cancelled'],
      'partially-approved': ['partially-paid', 'paid', 'denied', 'cancelled'],
      'partially-paid': ['partially-paid', 'paid'],
      paid: [],
      denied: [],
      cancelled: [],
    };
    return [claim.status, ...transitions[claim.status]];
  }

  protected saveInsuranceClaim(claim: InsuranceClaim): void {
    const edit = this.insuranceClaimEdit(claim);
    this.service
      .updateInsuranceClaim(claim.id, {
        status: edit.status,
        approvedAmount: edit.approvedAmount,
        paidAmount: edit.paidAmount,
        denialReason: edit.denialReason,
        notes: edit.notes,
      })
      .subscribe({
        next: (updated) => {
          this.insuranceClaims.update((claims) =>
            claims.map((item) => (item.id === updated.id ? updated : item)),
          );
          this.insuranceClaimEdits.set(updated.id, {
            status: updated.status,
            approvedAmount: updated.approvedAmount ?? null,
            paidAmount: updated.paidAmount,
            denialReason: updated.denialReason,
            notes: updated.notes,
          });
          this.notifications.success('Insurance claim status updated.');
          this.load();
        },
      });
  }

  protected onPmsCsvSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedPmsCsvFile.set(input.files?.[0] ?? null);
  }

  protected reconcilePmsCsv(): void {
    const file = this.selectedPmsCsvFile();
    if (!file) return;
    let mapping: Record<string, string>;
    try {
      mapping = JSON.parse(this.pmsMappingText()) as Record<string, string>;
    } catch {
      this.notifications.error('Enter a valid JSON field mapping.');
      return;
    }
    this.processingPmsCsv.set(true);
    this.service.reconcilePmsCsv(file, mapping).subscribe({
      next: (result) => {
        this.selectedPmsCsvFile.set(null);
        this.processingPmsCsv.set(false);
        this.notifications.success(
          `PMS reconciliation: ${result.matchedRows} matched, ${result.mismatchRows} mismatched, ${result.missingLocalRows} missing locally, ${result.missingPmsRows} missing in PMS.`,
        );
        this.loadPmsReconciliationRuns(result.id);
      },
      error: () => this.processingPmsCsv.set(false),
    });
  }

  protected loadPmsReconciliationRuns(selectRunId = ''): void {
    this.service.listPmsReconciliationRuns().subscribe({
      next: (runs) => {
        this.pmsReconciliationRuns.set(runs);
        const selected = selectRunId || this.selectedPmsRunId() || runs[0]?.id || '';
        this.selectedPmsRunId.set(selected);
        if (selected) this.loadPmsReconciliationRows(selected);
        else this.pmsReconciliationRows.set([]);
      },
    });
  }

  protected loadPmsReconciliationRows(runId: string): void {
    this.selectedPmsRunId.set(runId);
    this.service.listPmsReconciliationRows(runId).subscribe({
      next: (rows) => this.pmsReconciliationRows.set(rows),
    });
  }
  protected updateLedgerStage(stageId: string): void {
    this.ledgerForm.stageId = stageId;
    const stage = this.availableLedgerStages().find((item) => item.id === stageId);
    if (stage) this.ledgerForm.currency = stage.currency;
  }

  protected createVisit(): void {
    if (!this.visitForm.patientId) {
      this.notifications.error('Select a patient for this visit.');
      return;
    }
    if (
      (this.visitForm.status === 'scheduled' || this.visitForm.status === 'completed') &&
      !this.visitForm.visitAt
    ) {
      this.notifications.error('Choose the appointment or completion time.');
      return;
    }
    this.service
      .createVisit({
        patientId: this.visitForm.patientId,
        visitType: this.visitForm.visitType,
        status: this.visitForm.status,
        ...(this.visitForm.status === 'scheduled'
          ? { scheduledAt: new Date(this.visitForm.visitAt).toISOString() }
          : {}),
        ...(this.visitForm.status === 'completed'
          ? { completedAt: new Date(this.visitForm.visitAt).toISOString() }
          : {}),
        notes: this.visitForm.notes.trim(),
      })
      .subscribe({
        next: (visit) => {
          this.visits.update((items) => [visit, ...items]);
          this.visitForm.visitAt = '';
          this.visitForm.notes = '';
          this.notifications.success('Patient visit recorded.');
          this.load();
        },
      });
  }

  protected loadAnalytics(): void {
    const fromDate = this.analyticsFromDate()
      ? new Date(`${this.analyticsFromDate()}T00:00:00`).toISOString()
      : undefined;
    const toDate = this.analyticsToDate()
      ? new Date(`${this.analyticsToDate()}T23:59:59.999`).toISOString()
      : undefined;
    this.service.getAnalytics(fromDate, toDate).subscribe({
      next: (metrics) => this.analytics.set(metrics),
    });
  }

  protected createIntegration(): void {
    if (!this.integrationForm.provider) return;
    this.service
      .createIntegration({
        provider: this.integrationForm.provider,
        integrationType: this.integrationForm.integrationType,
        configurationJson: { connectorStatus: 'configured-by-clinic' },
      })
      .subscribe({
        next: (integration) => {
          this.integrations.update((items) => [integration, ...items]);
          this.integrationForm.provider = '';
        },
      });
  }

  protected createBranch(): void {
    if (!this.branchForm.name.trim()) return;
    this.service.createBranch({ ...this.branchForm }).subscribe({
      next: () => {
        this.notifications.success('Clinic branch added.');
        this.branchForm.name = '';
        this.branchForm.address = '';
        this.branchForm.phone = '';
        this.load();
      },
    });
  }

  protected inviteStaff(): void {
    if (!this.staffForm.fullName.trim() || !this.staffForm.email.trim() || !this.staffForm.branchId)
      return;
    this.service.inviteStaff({ ...this.staffForm }).subscribe({
      next: (invitation) => {
        this.staffInvitation.set(invitation);
        this.notifications.success('Staff invitation created. Share the one-time token securely.');
        this.staffForm.fullName = '';
        this.staffForm.email = '';
        this.load();
      },
    });
  }

  protected completeOnboarding(): void {
    this.service.completeOnboarding().subscribe({
      next: (status) => {
        this.onboarding.set(status);
        this.notifications.success('Clinic setup marked complete.');
      },
    });
  }

  protected createPortalInvitation(patientId: string): void {
    this.service.invitePatient(patientId).subscribe({
      next: (invitation) => {
        this.portalInvitation.set(invitation);
        this.notifications.success('Patient portal invitation created.');
      },
    });
  }

  protected portalInvitationUrl(): string {
    const invitation = this.portalInvitation();
    if (!invitation) return '';
    const params = new URLSearchParams({
      invite: invitation.invitationToken,
      clinicId: invitation.clinicId,
      email: invitation.email,
    });
    return `${window.location.origin}/patient-portal?${params}`;
  }

  protected staffInvitationUrl(): string {
    const invitation = this.staffInvitation();
    return invitation
      ? `${window.location.origin}/staff-invitation?token=${encodeURIComponent(invitation.invitationToken)}`
      : '';
  }

  protected onCsvSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedCsvFile.set(input.files?.[0] ?? null);
  }

  protected importCsv(): void {
    const file = this.selectedCsvFile();
    if (!file) return;
    let mapping: Record<string, string>;
    try {
      mapping = JSON.parse(this.csvMappingText()) as Record<string, string>;
    } catch {
      this.notifications.error('Enter a valid JSON field mapping.');
      return;
    }
    this.service.importCsv(file, mapping).subscribe({
      next: (job) => {
        this.notifications.success(
          `CSV import finished: ${job.processedCount} added, ${job.failedCount} rejected.`,
        );
        this.selectedCsvFile.set(null);
        this.load();
      },
    });
  }

  protected loadAudit(page = this.auditPage()): void {
    this.auditLoading.set(true);
    const filters = { ...this.auditFilters(), page, pageSize: this.auditPageSize() };
    forkJoin({
      list: this.service.listAudit(filters),
      summary: this.service.getAuditSummary(filters),
    }).subscribe({
      next: ({ list, summary }) => {
        this.audit.set(list.items);
        this.auditTotal.set(list.total);
        this.auditPage.set(list.page);
        this.auditPageSize.set(list.pageSize);
        this.auditTotalPages.set(list.totalPages);
        this.auditSummary.set(summary);
        this.auditLoading.set(false);
      },
      error: () => {
        this.auditLoading.set(false);
        this.notifications.error('Unable to load audit events.');
      },
    });
  }

  protected updateAuditFilter(key: keyof AuditFilters, value: string): void {
    this.auditFilters.update((f) => ({ ...f, [key]: value }));
  }

  protected applyAuditFilters(): void {
    this.auditPage.set(1);
    this.loadAudit(1);
  }

  protected clearAuditFilters(): void {
    this.auditFilters.set({
      q: '', action: '', resourceType: '', actorId: '', outcome: '', branchId: '',
      dateFrom: '', dateTo: '', eventId: '', ipAddress: '',
    });
    this.auditPage.set(1);
    this.loadAudit(1);
  }

  protected changeAuditPage(page: number): void {
    const next = Math.min(Math.max(1, page), this.auditTotalPages());
    this.loadAudit(next);
  }

  protected changeAuditPageSize(size: number): void {
    this.auditPageSize.set(size);
    this.auditPage.set(1);
    this.loadAudit(1);
  }

  protected openAuditEvent(event: AuditEvent): void {
    this.selectedAuditEvent.set(event);
  }

  protected closeAuditEvent(): void {
    this.selectedAuditEvent.set(null);
  }

  protected exportAuditCsv(): void {
    this.auditExporting.set(true);
    this.service.exportAuditCsv(this.auditFilters()).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'dentalpilot-audit-events.csv';
        link.click();
        URL.revokeObjectURL(url);
        this.auditExporting.set(false);
        this.notifications.success('Audit CSV export downloaded.');
        this.loadAudit(this.auditPage());
      },
      error: () => {
        this.auditExporting.set(false);
        this.notifications.error('Unable to export audit events.');
      },
    });
  }

  protected auditPageNumbers(): number[] {
    const total = this.auditTotalPages();
    const current = this.auditPage();
    const pages: number[] = [];
    const start = Math.max(1, current - 2);
    const end = Math.min(total, start + 4);
    for (let i = Math.max(1, end - 4); i <= end; i++) pages.push(i);
    return pages;
  }

  protected exportCsv(): void {
    this.exportingCsv.set(true);
    this.service.exportCsv().subscribe({
      next: (file) => {
        const url = URL.createObjectURL(file);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'dentalpilot-patients.csv';
        link.click();
        URL.revokeObjectURL(url);
        this.exportingCsv.set(false);
        this.notifications.success('Patient CSV export downloaded.');
      },
      error: () => this.exportingCsv.set(false),
    });
  }

  private load(): void {
    forkJoin({
      patients: this.service.listPatients(),
      enquiries: this.service.listEnquiries(),
      plans: this.service.listPlans(),
      records: this.service.listRecords(),
      reminders: this.service.listReminders(),
      audit: this.service.listAudit({ page: 1, pageSize: 25 }),
      auditSummary: this.service.getAuditSummary({}),
      integrations: this.service.listIntegrations(),
      consents: this.service.listConsents(),
      recovery: this.service.getRevenueRecovery(),
      analytics: this.service.getAnalytics(),
      visits: this.service.listVisits(),
      ledgerEntries: this.service.listTreatmentLedger(),
      insuranceClaims: this.service.listInsuranceClaims(),
      pmsRuns: this.service.listPmsReconciliationRuns(),
      recallSettings: this.service.getRecallSettings(),
      emailOutbox: this.service.listEmailOutbox(),
      branches: this.service.listBranches(),
      staff: this.service.listStaff(),
      onboarding: this.service.getOnboarding(),
      syncJobs: this.service.listSyncJobs(),
    }).subscribe({
      next: (result) => {
        this.patients.set(result.patients);
        this.enquiries.set(result.enquiries);
        this.plans.set(result.plans);
        this.records.set(result.records);
        this.reminders.set(result.reminders);
        this.audit.set(result.audit.items);
        this.auditTotal.set(result.audit.total);
        this.auditPage.set(result.audit.page);
        this.auditPageSize.set(result.audit.pageSize);
        this.auditTotalPages.set(result.audit.totalPages);
        this.auditSummary.set(result.auditSummary);
        this.integrations.set(result.integrations);
        this.consents.set(result.consents);
        this.recovery.set(result.recovery);
        this.analytics.set(result.analytics);
        this.visits.set(result.visits);
        this.ledgerEntries.set(result.ledgerEntries);
        this.insuranceClaims.set(result.insuranceClaims);
        this.pmsReconciliationRuns.set(result.pmsRuns);
        const selectedRunId = this.selectedPmsRunId() || result.pmsRuns[0]?.id || '';
        this.selectedPmsRunId.set(selectedRunId);
        if (selectedRunId) this.loadPmsReconciliationRows(selectedRunId);
        this.recallSettings.set(result.recallSettings);
        this.recallSettingsForm.postProcedureDays = result.recallSettings.postProcedureDays;
        this.recallSettingsForm.pendingTreatmentDays = result.recallSettings.pendingTreatmentDays;
        this.recallSettingsForm.hygieneRecallDays = result.recallSettings.hygieneRecallDays;
        this.emailOutbox.set(result.emailOutbox);
        this.branches.set(result.branches);
        this.staff.set(result.staff);
        this.onboarding.set(result.onboarding);
        this.syncJobs.set(result.syncJobs);
      },
      error: () => this.notifications.error('Unable to load clinic workflows. Please retry.'),
    });
  }
}
