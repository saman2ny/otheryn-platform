import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import {
  ClinicBranch,
  Patient,
  PatientVisit,
} from '../../core/models/healthcare.model';
import {
  AssetMaintenanceRecord,
  ClinicAsset,
  ClinicalAiSettings,
  ClinicalNoteDraft,
  DentalCaseStatus,
  DentalWorkflowCase,
  DentalWorkflowEvent,
  IntegrationCatalogEntry,
  MarketingPublicationDraft,
  PatientMessageDraft,
  SterilizationCycle,
} from '../../core/models/operations.model';
import { DentalPilotWorkflowsService } from '../dentalpilot-workflows/dentalpilot-workflows.service';
import { NotificationService } from '../../core/services/notification.service';
import { AuthService } from '../../core/services/auth.service';
import { PageHeader } from '../../shared/ui/page-header/page-header';
import { DentalOperationsService } from './dental-operations.service';

const TABS = [
  'digital',
  'equipment',
  'sterilization',
  'communication',
  'publishing',
  'documentation',
  'providers',
] as const;
type OperationsTab = (typeof TABS)[number];

const TITLES: Record<OperationsTab, string> = {
  digital: 'Digital dentistry cases',
  equipment: 'Equipment & maintenance',
  sterilization: 'Sterilisation monitoring',
  communication: 'Patient communication',
  publishing: 'Content publishing',
  documentation: 'Clinical documentation',
  providers: 'Connected providers',
};

const CASE_TRANSITIONS: Record<DentalCaseStatus, DentalCaseStatus[]> = {
  requested: ['planning', 'cancelled'],
  planning: ['in-progress', 'cancelled'],
  'in-progress': ['awaiting-clinician', 'cancelled'],
  'awaiting-clinician': ['in-progress', 'completed', 'cancelled'],
  completed: [],
  cancelled: [],
};

const MAINTENANCE_TRANSITIONS: Record<
  AssetMaintenanceRecord['status'],
  AssetMaintenanceRecord['status'][]
> = {
  planned: ['in-progress', 'cancelled'],
  'in-progress': ['completed', 'cancelled'],
  completed: [],
  cancelled: [],
};

@Component({
  selector: 'dp-dental-operations',
  imports: [DatePipe, FormsModule, PageHeader],
  templateUrl: './dental-operations.html',
})
export class DentalOperations {
  private readonly service = inject(DentalOperationsService);
  private readonly workflows = inject(DentalPilotWorkflowsService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly notifications = inject(NotificationService);
  private readonly auth = inject(AuthService);

  protected readonly activeTab = signal<OperationsTab>('digital');
  protected readonly title = computed(() => TITLES[this.activeTab()]);
  protected readonly tabs: { key: OperationsTab; label: string }[] = [
    { key: 'digital', label: 'Case coordination' },
    { key: 'equipment', label: 'Equipment' },
    { key: 'sterilization', label: 'Sterilisation' },
    { key: 'communication', label: 'Communication drafts' },
    { key: 'publishing', label: 'Publishing' },
    { key: 'documentation', label: 'Clinical notes' },
    { key: 'providers', label: 'Integrations' },
  ];
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly patients = signal<Patient[]>([]);
  protected readonly branches = signal<ClinicBranch[]>([]);
  protected readonly visits = signal<PatientVisit[]>([]);
  protected readonly cases = signal<DentalWorkflowCase[]>([]);
  protected readonly assets = signal<ClinicAsset[]>([]);
  protected readonly cycles = signal<SterilizationCycle[]>([]);
  protected readonly messageDrafts = signal<PatientMessageDraft[]>([]);
  protected readonly publications = signal<MarketingPublicationDraft[]>([]);
  protected readonly notes = signal<ClinicalNoteDraft[]>([]);
  protected readonly clinicalAiSettings = signal<ClinicalAiSettings | null>(null);
  protected readonly clinicalAiConsent = signal<Record<string, boolean>>({});
  protected readonly canManageClinic = this.auth.canManageClinic;
  protected readonly catalog = signal<IntegrationCatalogEntry[]>([]);
  protected readonly maintenance = signal<Record<string, AssetMaintenanceRecord[]>>({});
  protected readonly publicationSchedules = signal<Partial<Record<string, string>>>({});
  protected readonly selectedCaseId = signal('');
  protected readonly caseEvents = signal<DentalWorkflowEvent[]>([]);
  protected readonly selectedAssetId = signal('');

  protected readonly caseForm = {
    patientId: '',
    branchId: '',
    caseType: 'imaging' as DentalWorkflowCase['caseType'],
    title: '',
    providerName: '',
    externalReference: '',
    dueAt: '',
    details: '',
  };
  protected readonly eventForm = {
    eventType: 'milestone' as DentalWorkflowEvent['eventType'],
    title: '',
    notes: '',
  };
  protected readonly assetForm = {
    branchId: '',
    assetTag: '',
    assetType: 'dental-chair' as ClinicAsset['assetType'],
    displayName: '',
    modelName: '',
    serialNumber: '',
    nextServiceAt: '',
    notes: '',
  };
  protected readonly maintenanceForm = {
    workType: 'maintenance' as AssetMaintenanceRecord['workType'],
    dueAt: '',
    notes: '',
  };
  protected readonly cycleForm = {
    branchId: '',
    assetId: '',
    cycleReference: '',
    loadReference: '',
    result: 'passed' as SterilizationCycle['result'],
    startedAt: new Date().toISOString().slice(0, 16),
    completedAt: '',
    operatorName: '',
    notes: '',
  };
  protected readonly messageForm = {
    patientId: '',
    channel: 'email' as PatientMessageDraft['channel'],
    subject: '',
    body: '',
    consentConfirmed: false,
  };
  protected readonly publicationForm = {
    branchId: '',
    title: '',
    platform: 'google-business' as MarketingPublicationDraft['platform'],
    body: '',
    scheduledAt: '',
  };
  protected readonly noteForm = {
    patientId: '',
    visitId: '',
    title: '',
    clinicianInput: '',
  };

  constructor() {
    this.route.queryParamMap.subscribe((params) => {
      const tab = params.get('tab');
      this.activeTab.set(TABS.find((item) => item === tab) ?? 'digital');
    });
    this.load();
  }

  protected setTab(tab: OperationsTab): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { tab },
      queryParamsHandling: 'merge',
    });
  }

  protected patientName(id: string): string {
    return this.patients().find((patient) => patient.id === id)?.fullName ?? 'Unknown patient';
  }

  protected branchName(id?: string): string {
    return this.branches().find((branch) => branch.id === id)?.name ?? 'Clinic-wide';
  }

  protected assetName(id: string): string {
    return this.assets().find((asset) => asset.id === id)?.displayName ?? 'Unknown asset';
  }

  protected caseStatuses(status: DentalCaseStatus): DentalCaseStatus[] {
    return [status, ...CASE_TRANSITIONS[status]];
  }

  protected createCase(): void {
    let details: Record<string, unknown> = {};
    try {
      details = this.caseForm.details.trim() ? JSON.parse(this.caseForm.details) : {};
      if (!details || Array.isArray(details) || typeof details !== 'object') {
        throw new Error('Details must be a JSON object.');
      }
    } catch {
      this.notifications.error('Enter case details as a valid JSON object.');
      return;
    }
    if (!this.caseForm.patientId || this.caseForm.title.trim().length < 2) {
      this.notifications.error('Select a patient and enter a case title.');
      return;
    }
    this.saving.set(true);
    this.service
      .createCase({
        patientId: this.caseForm.patientId,
        ...(this.caseForm.branchId ? { branchId: this.caseForm.branchId } : {}),
        caseType: this.caseForm.caseType,
        title: this.caseForm.title.trim(),
        providerName: this.caseForm.providerName.trim(),
        externalReference: this.caseForm.externalReference.trim(),
        ...(this.caseForm.dueAt ? { dueAt: new Date(this.caseForm.dueAt).toISOString() } : {}),
        details,
      })
      .subscribe({
        next: (created) => {
          this.cases.update((items) => [created, ...items]);
          this.caseForm.title = '';
          this.caseForm.providerName = '';
          this.caseForm.externalReference = '';
          this.caseForm.dueAt = '';
          this.caseForm.details = '';
          this.saving.set(false);
          this.notifications.success('Dental case added to the clinic workflow.');
        },
        error: () => this.saving.set(false),
      });
  }

  protected updateCaseStatus(id: string, status: DentalCaseStatus): void {
    this.service.updateCaseStatus(id, status).subscribe({
      next: (updated) => {
        this.cases.update((items) => items.map((item) => (item.id === id ? updated : item)));
        this.notifications.success('Case status updated.');
      },
    });
  }

  protected selectCase(id: string): void {
    this.selectedCaseId.set(id);
    this.service.listCaseEvents(id).subscribe({
      next: (events) => {
        if (this.selectedCaseId() === id) this.caseEvents.set(events);
      },
    });
  }

  protected addCaseEvent(): void {
    const caseId = this.selectedCaseId();
    if (!caseId || this.eventForm.title.trim().length < 2) {
      this.notifications.error('Select a case and enter a milestone title.');
      return;
    }
    this.service
      .createCaseEvent(caseId, {
        ...this.eventForm,
        title: this.eventForm.title.trim(),
        notes: this.eventForm.notes.trim(),
      })
      .subscribe({
        next: (event) => {
          this.caseEvents.update((items) => [...items, event]);
          this.eventForm.title = '';
          this.eventForm.notes = '';
          this.notifications.success('Case event added to the timeline.');
        },
      });
  }

  protected createAsset(): void {
    if (!this.assetForm.branchId || this.assetForm.assetTag.trim().length < 2) {
      this.notifications.error('Select a branch and provide a unique asset tag.');
      return;
    }
    this.saving.set(true);
    this.service
      .createAsset({
        ...this.assetForm,
        assetTag: this.assetForm.assetTag.trim(),
        displayName: this.assetForm.displayName.trim(),
        modelName: this.assetForm.modelName.trim(),
        serialNumber: this.assetForm.serialNumber.trim(),
        notes: this.assetForm.notes.trim(),
        ...(this.assetForm.nextServiceAt
          ? { nextServiceAt: new Date(this.assetForm.nextServiceAt).toISOString() }
          : {}),
      })
      .subscribe({
        next: (asset) => {
          this.assets.update((items) => [asset, ...items]);
          this.assetForm.assetTag = '';
          this.assetForm.displayName = '';
          this.assetForm.modelName = '';
          this.assetForm.serialNumber = '';
          this.assetForm.nextServiceAt = '';
          this.assetForm.notes = '';
          this.saving.set(false);
          this.notifications.success('Clinic asset registered.');
        },
        error: () => this.saving.set(false),
      });
  }

  protected updateAssetStatus(asset: ClinicAsset, status: ClinicAsset['status']): void {
    this.service.updateAsset(asset.id, { status }).subscribe({
      next: (updated) => {
        this.assets.update((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      },
    });
  }

  protected showMaintenance(assetId: string): void {
    this.selectedAssetId.set(assetId);
    this.service.listMaintenance(assetId).subscribe({
      next: (items) => {
        if (this.selectedAssetId() === assetId) {
          this.maintenance.update((current) => ({ ...current, [assetId]: items }));
        }
      },
    });
  }

  protected createMaintenance(): void {
    const assetId = this.selectedAssetId();
    if (!assetId) {
      this.notifications.error('Choose an equipment asset first.');
      return;
    }
    this.service
      .createMaintenance(assetId, {
        workType: this.maintenanceForm.workType,
        notes: this.maintenanceForm.notes.trim(),
        ...(this.maintenanceForm.dueAt
          ? { dueAt: new Date(this.maintenanceForm.dueAt).toISOString() }
          : {}),
      })
      .subscribe({
        next: (record) => {
          this.maintenance.update((items) => ({
            ...items,
            [assetId]: [record, ...(items[assetId] ?? [])],
          }));
          this.maintenanceForm.notes = '';
          this.maintenanceForm.dueAt = '';
          this.notifications.success('Maintenance item scheduled.');
        },
      });
  }

  protected updateMaintenanceStatus(
    assetId: string,
    record: AssetMaintenanceRecord,
    status: AssetMaintenanceRecord['status'],
  ): void {
    this.service.updateMaintenance(assetId, record.id, { status, notes: record.notes }).subscribe({
      next: (updated) =>
        this.maintenance.update((items) => ({
          ...items,
          [assetId]: (items[assetId] ?? []).map((item) =>
            item.id === updated.id ? updated : item,
          ),
        })),
    });
  }

  protected createCycle(): void {
    if (!this.cycleForm.assetId || !this.cycleForm.operatorName.trim()) {
      this.notifications.error('Select an autoclave and enter the operator name.');
      return;
    }
    this.service
      .createSterilizationCycle({
        ...this.cycleForm,
        startedAt: new Date(this.cycleForm.startedAt).toISOString(),
        ...(this.cycleForm.completedAt
          ? { completedAt: new Date(this.cycleForm.completedAt).toISOString() }
          : {}),
        cycleReference: this.cycleForm.cycleReference.trim(),
        loadReference: this.cycleForm.loadReference.trim(),
        operatorName: this.cycleForm.operatorName.trim(),
        notes: this.cycleForm.notes.trim(),
      })
      .subscribe({
        next: (cycle) => {
          this.cycles.update((items) => [cycle, ...items]);
          if (cycle.result === 'failed') {
            this.assets.update((items) =>
              items.map((asset) =>
                asset.id === cycle.assetId ? { ...asset, status: 'unavailable' } : asset,
              ),
            );
          }
          this.cycleForm.cycleReference = '';
          this.cycleForm.loadReference = '';
          this.cycleForm.notes = '';
          this.notifications.success('Sterilisation cycle recorded.');
        },
      });
  }

  protected createMessageDraft(): void {
    if (!this.messageForm.patientId || !this.messageForm.consentConfirmed) {
      this.notifications.error('Select a patient and confirm current channel consent.');
      return;
    }
    this.service
      .createMessageDraft({
        patientId: this.messageForm.patientId,
        channel: this.messageForm.channel,
        subject: this.messageForm.subject.trim(),
        body: this.messageForm.body.trim(),
        consentConfirmed: this.messageForm.consentConfirmed,
      })
      .subscribe({
        next: (draft) => {
          this.messageDrafts.update((items) => [draft, ...items]);
          this.messageForm.subject = '';
          this.messageForm.body = '';
          this.messageForm.consentConfirmed = false;
          this.notifications.success('Communication draft saved; no message was sent.');
        },
      });
  }

  protected updateMessageStatus(draft: PatientMessageDraft, status: 'approved' | 'cancelled'): void {
    this.service.updateMessageDraft(draft.id, status).subscribe({
      next: (updated) =>
        this.messageDrafts.update((items) =>
          items.map((item) => (item.id === updated.id ? updated : item)),
        ),
    });
  }

  protected createPublication(): void {
    if (this.publicationForm.title.trim().length < 2 || !this.publicationForm.body.trim()) {
      this.notifications.error('Enter a publication title and content.');
      return;
    }
    this.service
      .createPublication({
        ...(this.publicationForm.branchId ? { branchId: this.publicationForm.branchId } : {}),
        title: this.publicationForm.title.trim(),
        platform: this.publicationForm.platform,
        body: this.publicationForm.body.trim(),
        ...(this.publicationForm.scheduledAt
          ? { scheduledAt: new Date(this.publicationForm.scheduledAt).toISOString() }
          : {}),
      })
      .subscribe({
        next: (draft) => {
          this.publications.update((items) => [draft, ...items]);
          this.publicationForm.title = '';
          this.publicationForm.body = '';
          this.publicationForm.scheduledAt = '';
          this.notifications.success('Publication draft saved; it was not posted externally.');
        },
      });
  }

  protected updatePublicationStatus(
    draft: MarketingPublicationDraft,
    status: MarketingPublicationDraft['status'],
    scheduleValue?: string,
  ): void {
    const scheduledAt =
      status === 'scheduled' && (scheduleValue || this.publicationForm.scheduledAt)
        ? new Date(scheduleValue || this.publicationForm.scheduledAt).toISOString()
        : draft.scheduledAt;
    this.service.updatePublication(draft.id, status, scheduledAt).subscribe({
      next: (updated) =>
        this.publications.update((items) =>
          items.map((item) => (item.id === updated.id ? updated : item)),
        ),
    });
  }

  protected setPublicationSchedule(id: string, value: string): void {
    this.publicationSchedules.update((schedules) => ({ ...schedules, [id]: value }));
  }

  protected schedulePublication(draft: MarketingPublicationDraft): void {
    const value = this.publicationSchedules()[draft.id];
    if (!value) {
      this.notifications.error('Choose the time before marking this publication as scheduled.');
      return;
    }
    this.updatePublicationStatus(draft, 'scheduled', value);
  }

  protected maintenanceStatuses(
    status: AssetMaintenanceRecord['status'],
  ): AssetMaintenanceRecord['status'][] {
    return [status, ...MAINTENANCE_TRANSITIONS[status]];
  }

  protected createClinicalNote(): void {
    if (!this.noteForm.patientId || this.noteForm.clinicianInput.trim().length < 10) {
      this.notifications.error('Select a patient and enter clinician-authored notes.');
      return;
    }
    this.service
      .createClinicalNoteDraft({
        patientId: this.noteForm.patientId,
        ...(this.noteForm.visitId ? { visitId: this.noteForm.visitId } : {}),
        title: this.noteForm.title.trim(),
        clinicianInput: this.noteForm.clinicianInput.trim(),
      })
      .subscribe({
        next: (note) => {
          this.notes.update((items) => [note, ...items]);
          this.noteForm.title = '';
          this.noteForm.clinicianInput = '';
          this.notifications.success('Clinician-entered note draft saved for review.');
        },
      });
  }

  protected updateClinicalAiConsent(noteId: string, confirmed: boolean): void {
    this.clinicalAiConsent.update((consents) => ({ ...consents, [noteId]: confirmed }));
  }

  protected setClinicClinicalAiEnabled(enabled: boolean): void {
    this.saving.set(true);
    this.service.updateClinicalAiSettings(enabled).subscribe({
      next: (settings) => {
        this.clinicalAiSettings.set(settings);
        this.saving.set(false);
        this.notifications.success(
          enabled ? 'Clinical note drafting enabled for this clinic.' : 'Clinical note drafting disabled.',
        );
      },
      error: () => this.saving.set(false),
    });
  }

  protected generateClinicalNote(note: ClinicalNoteDraft): void {
    if (!this.clinicalAiConsent()[note.id]) {
      this.notifications.error('Confirm the patient’s consent before generating a note draft.');
      return;
    }
    this.saving.set(true);
    this.service.generateClinicalNoteDraft(note.id, true).subscribe({
      next: (updated) => {
        this.notes.update((items) => items.map((item) => (item.id === updated.id ? updated : item)));
        this.updateClinicalAiConsent(note.id, false);
        this.saving.set(false);
        this.notifications.success('AI-assisted draft saved for clinician review; it is not a diagnosis.');
      },
      error: () => this.saving.set(false),
    });
  }

  protected reviewNote(note: ClinicalNoteDraft, reviewStatus: 'approved' | 'rejected'): void {
    this.service.reviewClinicalNoteDraft(note.id, reviewStatus).subscribe({
      next: (updated) =>
        this.notes.update((items) =>
          items.map((item) => (item.id === updated.id ? updated : item)),
        ),
    });
  }

  protected maintenanceRows(assetId: string): AssetMaintenanceRecord[] {
    return this.maintenance()[assetId] ?? [];
  }

  protected integrationsByType(type: string): IntegrationCatalogEntry[] {
    return this.catalog().filter((entry) => entry.integrationType === type);
  }

  private load(): void {
    forkJoin({
      patients: this.workflows.listPatients(),
      branches: this.workflows.listBranches(),
      visits: this.workflows.listVisits(),
      cases: this.service.listCases(),
      assets: this.service.listAssets(),
      cycles: this.service.listSterilizationCycles(),
      messages: this.service.listMessageDrafts(),
      publications: this.service.listPublications(),
      notes: this.service.listClinicalNoteDrafts(),
      clinicalAiSettings: this.service.getClinicalAiSettings(),
      catalog: this.service.listIntegrationCatalog(),
    }).subscribe({
      next: (result) => {
        this.patients.set(result.patients);
        this.branches.set(result.branches);
        this.visits.set(result.visits);
        this.cases.set(result.cases);
        this.assets.set(result.assets);
        this.cycles.set(result.cycles);
        this.messageDrafts.set(result.messages);
        this.publications.set(result.publications);
        this.notes.set(result.notes);
        this.clinicalAiSettings.set(result.clinicalAiSettings);
        this.catalog.set(result.catalog);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.notifications.error('Unable to load dental operations data. Please retry.');
      },
    });
  }
}
