import { HttpClient, HttpResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';
import { ExportJob, ExportRequest } from '../../core/models/export.model';

@Injectable({ providedIn: 'root' })
export class ExportContentService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  createJob(request: ExportRequest): Observable<ExportJob> {
    return this.http.post<ExportJob>(`${this.baseUrl}/${API_ENDPOINTS.export.create}`, request);
  }

  listJobs(): Observable<ExportJob[]> {
    return this.http.get<ExportJob[]>(`${this.baseUrl}/${API_ENDPOINTS.export.create}`);
  }

  /**
   * Blob + full response, not a plain URL — a bare <a href> download can't carry the auth
   * header, and reading the response lets us reuse the filename the backend already picked
   * (single PNG vs. zip of several) instead of re-deriving that rule client-side.
   */
  download(jobId: string): Observable<HttpResponse<Blob>> {
    return this.http.get(`${this.baseUrl}/${API_ENDPOINTS.export.download(jobId)}`, {
      responseType: 'blob',
      observe: 'response',
    });
  }
}
