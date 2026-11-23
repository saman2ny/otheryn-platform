import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';
import { ClinicProfile, UpdateClinicProfileRequest } from '../../core/models/clinic.model';

@Injectable({ providedIn: 'root' })
export class ClinicProfileService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  getProfile(): Observable<ClinicProfile> {
    return this.http.get<ClinicProfile>(`${this.baseUrl}/${API_ENDPOINTS.clinic.profile}`);
  }

  updateProfile(request: UpdateClinicProfileRequest): Observable<ClinicProfile> {
    return this.http.put<ClinicProfile>(`${this.baseUrl}/${API_ENDPOINTS.clinic.profile}`, request);
  }
}
