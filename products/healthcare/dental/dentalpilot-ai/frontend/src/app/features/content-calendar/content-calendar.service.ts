import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';
import { CalendarEvent, CreateCalendarEventRequest } from '../../core/models/calendar.model';

@Injectable({ providedIn: 'root' })
export class ContentCalendarService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  list(): Observable<CalendarEvent[]> {
    return this.http.get<CalendarEvent[]>(`${this.baseUrl}/${API_ENDPOINTS.calendar.events}`);
  }

  create(request: CreateCalendarEventRequest): Observable<CalendarEvent> {
    return this.http.post<CalendarEvent>(
      `${this.baseUrl}/${API_ENDPOINTS.calendar.events}`,
      request,
    );
  }

  remove(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${API_ENDPOINTS.calendar.eventById(id)}`);
  }
}
