import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';
import { GenerateContentRequest, GeneratedContent } from '../../core/models/content.model';

@Injectable({ providedIn: 'root' })
export class ContentGeneratorService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  generate(request: GenerateContentRequest): Observable<GeneratedContent> {
    return this.http.post<GeneratedContent>(
      `${this.baseUrl}/${API_ENDPOINTS.content.generate}`,
      request,
    );
  }

  list(): Observable<GeneratedContent[]> {
    return this.http.get<GeneratedContent[]>(`${this.baseUrl}/${API_ENDPOINTS.content.list}`);
  }
}
