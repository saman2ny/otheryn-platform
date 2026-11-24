import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';
import {
  AssetMaintenanceRecord,
  ClinicAsset,
  ClinicAssetCreate,
  ClinicalAiSettings,
  ClinicalNoteDraft,
  DentalWorkflowCase,
  DentalWorkflowCaseCreate,
  DentalWorkflowEvent,
  IntegrationCatalogEntry,
  MarketingPublicationDraft,
  PatientMessageDraft,
  SterilizationCycle,
} from '../../core/models/operations.model';

@Injectable({ providedIn: 'root' })
export class DentalOperationsService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  listCases(): Observable<DentalWorkflowCase[]> {
    return this.http.get<DentalWorkflowCase[]>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.dentalCases}`,
    );
  }

  createCase(payload: DentalWorkflowCaseCreate): Observable<DentalWorkflowCase> {
    return this.http.post<DentalWorkflowCase>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.dentalCases}`,
      payload,
    );
  }

  updateCaseStatus(
    id: string,
    status: DentalWorkflowCase['status'],
  ): Observable<DentalWorkflowCase> {
    return this.http.patch<DentalWorkflowCase>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.dentalCaseById(id)}`,
      { status },
    );
  }

  listCaseEvents(id: string): Observable<DentalWorkflowEvent[]> {
    return this.http.get<DentalWorkflowEvent[]>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.dentalCaseEvents(id)}`,
    );
  }

  createCaseEvent(
    id: string,
    payload: Pick<DentalWorkflowEvent, 'eventType' | 'title' | 'notes'>,
  ): Observable<DentalWorkflowEvent> {
    return this.http.post<DentalWorkflowEvent>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.dentalCaseEvents(id)}`,
      payload,
    );
  }

  listAssets(): Observable<ClinicAsset[]> {
    return this.http.get<ClinicAsset[]>(`${this.baseUrl}/${API_ENDPOINTS.operations.assets}`);
  }

  createAsset(payload: ClinicAssetCreate): Observable<ClinicAsset> {
    return this.http.post<ClinicAsset>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.assets}`,
      payload,
    );
  }

  updateAsset(
    id: string,
    payload: Partial<Pick<ClinicAsset, 'status' | 'nextServiceAt' | 'notes'>>,
  ): Observable<ClinicAsset> {
    return this.http.patch<ClinicAsset>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.assetById(id)}`,
      payload,
    );
  }

  listMaintenance(assetId: string): Observable<AssetMaintenanceRecord[]> {
    return this.http.get<AssetMaintenanceRecord[]>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.assetMaintenance(assetId)}`,
    );
  }

  createMaintenance(
    assetId: string,
    payload: Pick<AssetMaintenanceRecord, 'workType' | 'dueAt' | 'notes'>,
  ): Observable<AssetMaintenanceRecord> {
    return this.http.post<AssetMaintenanceRecord>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.assetMaintenance(assetId)}`,
      payload,
    );
  }

  updateMaintenance(
    assetId: string,
    recordId: string,
    payload: Pick<AssetMaintenanceRecord, 'status' | 'notes'>,
  ): Observable<AssetMaintenanceRecord> {
    return this.http.patch<AssetMaintenanceRecord>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.assetMaintenanceById(assetId, recordId)}`,
      payload,
    );
  }

  listSterilizationCycles(): Observable<SterilizationCycle[]> {
    return this.http.get<SterilizationCycle[]>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.sterilizationCycles}`,
    );
  }

  createSterilizationCycle(
    payload: Omit<SterilizationCycle, 'id' | 'recordedBy' | 'createdAt'>,
  ): Observable<SterilizationCycle> {
    return this.http.post<SterilizationCycle>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.sterilizationCycles}`,
      payload,
    );
  }

  listMessageDrafts(): Observable<PatientMessageDraft[]> {
    return this.http.get<PatientMessageDraft[]>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.messageDrafts}`,
    );
  }

  createMessageDraft(
    payload: Pick<
      PatientMessageDraft,
      'patientId' | 'branchId' | 'channel' | 'subject' | 'body' | 'consentConfirmed'
    >,
  ): Observable<PatientMessageDraft> {
    return this.http.post<PatientMessageDraft>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.messageDrafts}`,
      payload,
    );
  }

  updateMessageDraft(
    id: string,
    status: 'approved' | 'cancelled',
  ): Observable<PatientMessageDraft> {
    return this.http.patch<PatientMessageDraft>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.messageDraftById(id)}`,
      { status },
    );
  }

  listPublications(): Observable<MarketingPublicationDraft[]> {
    return this.http.get<MarketingPublicationDraft[]>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.marketingPublications}`,
    );
  }

  createPublication(
    payload: Pick<
      MarketingPublicationDraft,
      'branchId' | 'title' | 'platform' | 'body' | 'scheduledAt'
    >,
  ): Observable<MarketingPublicationDraft> {
    return this.http.post<MarketingPublicationDraft>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.marketingPublications}`,
      payload,
    );
  }

  updatePublication(
    id: string,
    status: MarketingPublicationDraft['status'],
    scheduledAt?: string,
  ): Observable<MarketingPublicationDraft> {
    return this.http.patch<MarketingPublicationDraft>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.marketingPublicationById(id)}`,
      { status, ...(scheduledAt ? { scheduledAt } : {}) },
    );
  }

  listClinicalNoteDrafts(): Observable<ClinicalNoteDraft[]> {
    return this.http.get<ClinicalNoteDraft[]>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.clinicalNoteDrafts}`,
    );
  }

  getClinicalAiSettings(): Observable<ClinicalAiSettings> {
    return this.http.get<ClinicalAiSettings>(
      `${this.baseUrl}/${API_ENDPOINTS.clinic.clinicalAiSettings}`,
    );
  }

  updateClinicalAiSettings(enabled: boolean): Observable<ClinicalAiSettings> {
    return this.http.patch<ClinicalAiSettings>(
      `${this.baseUrl}/${API_ENDPOINTS.clinic.clinicalAiSettings}`,
      { enabled },
    );
  }

  createClinicalNoteDraft(
    payload: Pick<ClinicalNoteDraft, 'patientId' | 'visitId' | 'title' | 'clinicianInput'>,
  ): Observable<ClinicalNoteDraft> {
    return this.http.post<ClinicalNoteDraft>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.clinicalNoteDrafts}`,
      payload,
    );
  }

  generateClinicalNoteDraft(
    id: string,
    patientConsentConfirmed: boolean,
  ): Observable<ClinicalNoteDraft> {
    return this.http.post<ClinicalNoteDraft>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.generateClinicalNote(id)}`,
      { patientConsentConfirmed },
    );
  }

  reviewClinicalNoteDraft(
    id: string,
    reviewStatus: 'approved' | 'rejected',
  ): Observable<ClinicalNoteDraft> {
    return this.http.patch<ClinicalNoteDraft>(
      `${this.baseUrl}/${API_ENDPOINTS.operations.reviewClinicalNoteDraft(id)}`,
      { reviewStatus },
    );
  }

  listIntegrationCatalog(): Observable<IntegrationCatalogEntry[]> {
    return this.http.get<IntegrationCatalogEntry[]>(
      `${this.baseUrl}/${API_ENDPOINTS.integrations.catalog}`,
    );
  }
}
