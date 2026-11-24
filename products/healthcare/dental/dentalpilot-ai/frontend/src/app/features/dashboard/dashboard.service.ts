import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';
import {
  DashboardSummary,
  RevenueMetrics,
  FinancialSummary,
  TreatmentFollowupMetrics,
  PatientRetentionMetrics,
  ClinicOperationalMetrics,
  OnboardingStatus,
} from '../../core/models/dashboard.model';

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  getSummary(): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>(`${this.baseUrl}/${API_ENDPOINTS.dashboard.summary}`);
  }

  getRevenueMetrics(fromDate?: string, toDate?: string): Observable<RevenueMetrics> {
    const params = new URLSearchParams();
    if (fromDate) params.set('from_date', fromDate);
    if (toDate) params.set('to_date', toDate);
    return this.http.get<RevenueMetrics>(
      `${this.baseUrl}/${API_ENDPOINTS.dashboard.revenue}?${params}`,
    );
  }

  getFinancialSummary(fromDate?: string, toDate?: string): Observable<FinancialSummary> {
    const params = new URLSearchParams();
    if (fromDate) params.set('from_date', fromDate);
    if (toDate) params.set('to_date', toDate);
    return this.http.get<FinancialSummary>(
      `${this.baseUrl}/${API_ENDPOINTS.dashboard.financialSummary}?${params}`,
    );
  }

  getTreatmentFollowupMetrics(
    fromDate?: string,
    toDate?: string,
  ): Observable<TreatmentFollowupMetrics> {
    const params = new URLSearchParams();
    if (fromDate) params.set('from_date', fromDate);
    if (toDate) params.set('to_date', toDate);
    return this.http.get<TreatmentFollowupMetrics>(
      `${this.baseUrl}/${API_ENDPOINTS.dashboard.treatmentFollowup}?${params}`,
    );
  }

  getPatientRetentionMetrics(
    fromDate?: string,
    toDate?: string,
  ): Observable<PatientRetentionMetrics> {
    const params = new URLSearchParams();
    if (fromDate) params.set('from_date', fromDate);
    if (toDate) params.set('to_date', toDate);
    return this.http.get<PatientRetentionMetrics>(
      `${this.baseUrl}/${API_ENDPOINTS.dashboard.patientRetention}?${params}`,
    );
  }

  getOperationalMetrics(fromDate?: string, toDate?: string): Observable<ClinicOperationalMetrics> {
    const params = new URLSearchParams();
    if (fromDate) params.set('from_date', fromDate);
    if (toDate) params.set('to_date', toDate);
    return this.http.get<ClinicOperationalMetrics>(
      `${this.baseUrl}/${API_ENDPOINTS.dashboard.operational}?${params}`,
    );
  }

  getOnboardingStatus(): Observable<OnboardingStatus> {
    return this.http.get<OnboardingStatus>(`${this.baseUrl}/${API_ENDPOINTS.clinic.onboarding}`);
  }
}
