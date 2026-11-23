import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';
import { ClinicBranch } from '../../core/models/healthcare.model';
import {
  CampaignStatus,
  ClinicReview,
  ClinicReviewInput,
  LocalListingAudit,
  LocalListingAuditInput,
  MarketingCampaign,
  MarketingCampaignInput,
} from '../../core/models/growth.model';

@Injectable({ providedIn: 'root' })
export class ClinicGrowthOsService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  listBranches(): Observable<ClinicBranch[]> {
    return this.http.get<ClinicBranch[]>(`${this.baseUrl}/${API_ENDPOINTS.clinic.branches}`);
  }

  listLocalListings(): Observable<LocalListingAudit[]> {
    return this.http.get<LocalListingAudit[]>(
      `${this.baseUrl}/${API_ENDPOINTS.growth.localListings}`,
    );
  }

  saveLocalListing(payload: LocalListingAuditInput): Observable<LocalListingAudit> {
    return this.http.post<LocalListingAudit>(
      `${this.baseUrl}/${API_ENDPOINTS.growth.localListings}`,
      payload,
    );
  }

  listCampaigns(): Observable<MarketingCampaign[]> {
    return this.http.get<MarketingCampaign[]>(`${this.baseUrl}/${API_ENDPOINTS.growth.campaigns}`);
  }

  createCampaign(payload: MarketingCampaignInput): Observable<MarketingCampaign> {
    return this.http.post<MarketingCampaign>(
      `${this.baseUrl}/${API_ENDPOINTS.growth.campaigns}`,
      payload,
    );
  }

  updateCampaignStatus(campaignId: string, status: CampaignStatus): Observable<MarketingCampaign> {
    return this.http.patch<MarketingCampaign>(
      `${this.baseUrl}/${API_ENDPOINTS.growth.campaignById(campaignId)}`,
      { status },
    );
  }

  listReviews(): Observable<ClinicReview[]> {
    return this.http.get<ClinicReview[]>(`${this.baseUrl}/${API_ENDPOINTS.growth.reviews}`);
  }

  createReview(payload: ClinicReviewInput): Observable<ClinicReview> {
    return this.http.post<ClinicReview>(`${this.baseUrl}/${API_ENDPOINTS.growth.reviews}`, payload);
  }

  saveReviewDraft(reviewId: string, responseDraft: string): Observable<ClinicReview> {
    return this.http.patch<ClinicReview>(
      `${this.baseUrl}/${API_ENDPOINTS.growth.reviewById(reviewId)}`,
      { responseDraft },
    );
  }
}
