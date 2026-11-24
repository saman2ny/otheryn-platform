import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';
import {
  Invoice,
  Subscription,
  SubscriptionPlan,
  SubscriptionCheckoutRequest,
  SubscriptionCheckoutResponse,
  VerifySubscriptionRequest,
} from '../../core/models/billing.model';

@Injectable({ providedIn: 'root' })
export class BillingService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  getPlans(): Observable<SubscriptionPlan[]> {
    return this.http.get<SubscriptionPlan[]>(`${this.baseUrl}/${API_ENDPOINTS.billing.plans}`);
  }

  getSubscription(): Observable<Subscription> {
    return this.http.get<Subscription>(`${this.baseUrl}/${API_ENDPOINTS.billing.subscription}`);
  }

  getInvoices(): Observable<Invoice[]> {
    return this.http.get<Invoice[]>(`${this.baseUrl}/${API_ENDPOINTS.billing.invoices}`);
  }

  createSubscription(
    request: SubscriptionCheckoutRequest,
  ): Observable<SubscriptionCheckoutResponse> {
    return this.http.post<SubscriptionCheckoutResponse>(
      `${this.baseUrl}/${API_ENDPOINTS.billing.createSubscription}`,
      request,
    );
  }

  verifySubscription(request: VerifySubscriptionRequest): Observable<Subscription> {
    return this.http.post<Subscription>(
      `${this.baseUrl}/${API_ENDPOINTS.billing.verifySubscription}`,
      request,
    );
  }

  cancelSubscription(cancelAtCycleEnd = true): Observable<Subscription> {
    return this.http.post<Subscription>(
      `${this.baseUrl}/${API_ENDPOINTS.billing.cancelSubscription}`,
      { cancelAtCycleEnd },
    );
  }

  pauseSubscription(): Observable<Subscription> {
    return this.http.post<Subscription>(
      `${this.baseUrl}/${API_ENDPOINTS.billing.pauseSubscription}`,
      {},
    );
  }

  resumeSubscription(): Observable<Subscription> {
    return this.http.post<Subscription>(
      `${this.baseUrl}/${API_ENDPOINTS.billing.resumeSubscription}`,
      {},
    );
  }
}
