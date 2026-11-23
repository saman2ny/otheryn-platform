import { DatePipe } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { environment } from '../../../environments/environment';
import {
  HealthRecord,
  Patient,
  PatientPortalLogin,
  PatientPortalShare,
  PatientPortalSharedRecords,
} from '../../core/models/healthcare.model';
import {
  PatientPortalTreatmentCharge,
  TreatmentPaymentOrder,
  TreatmentPaymentVerify,
} from '../../core/models/billing.model';
import { NotificationService } from '../../core/services/notification.service';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';

@Component({
  selector: 'dp-patient-portal',
  imports: [DatePipe, FormsModule],
  templateUrl: './patient-portal.html',
})
export class PatientPortal {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly notifications = inject(NotificationService);
  private readonly baseUrl = environment.apiBaseUrl;

  protected readonly accessToken = signal('');
  protected readonly patient = signal<Patient | null>(null);
  protected readonly records = signal<HealthRecord[]>([]);
  protected readonly treatmentCharges = signal<PatientPortalTreatmentCharge[]>([]);
  protected readonly selectedRecordIds = signal<Set<string>>(new Set());
  protected readonly shared = signal<PatientPortalSharedRecords | null>(null);
  protected readonly invitationToken = signal('');
  protected readonly shareToken = signal('');
  protected readonly shareLink = signal('');
  protected readonly isSharedView = computed(() => this.shareToken().length > 0);
  protected readonly loginForm = { clinicId: '', email: '', password: '' };
  protected readonly activationForm = { password: '' };
  protected readonly shareForm = {
    purpose: 'Share records with another care provider',
    recipientName: '',
  };
  protected readonly loading = signal(false);
  protected readonly payingChargeId = signal('');

  constructor() {
    this.route.queryParamMap.subscribe((params) => {
      const invitation = params.get('invite');
      const share = params.get('share');
      if (invitation) this.invitationToken.set(invitation);
      const clinicId = params.get('clinicId');
      const email = params.get('email');
      if (clinicId) this.loginForm.clinicId = clinicId;
      if (email) this.loginForm.email = email;
      if (share) {
        this.shareToken.set(share);
        this.loadSharedRecords(share);
      }
    });
  }

  protected activateInvitation(): void {
    if (!this.invitationToken() || this.activationForm.password.length < 12) {
      this.notifications.error(
        'Enter a valid invitation token and a password of at least 12 characters.',
      );
      return;
    }
    this.loading.set(true);
    this.http
      .post<void>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.acceptPortalInvitation}`, {
        invitationToken: this.invitationToken(),
        password: this.activationForm.password,
      })
      .subscribe({
        next: () => {
          this.loading.set(false);
          this.invitationToken.set('');
          this.activationForm.password = '';
          this.notifications.success(
            'Portal account activated. Sign in with your clinic and email.',
          );
        },
        error: () => this.loading.set(false),
      });
  }

  protected updateInvitationToken(event: Event): void {
    this.invitationToken.set((event.target as HTMLInputElement).value);
  }

  protected login(): void {
    this.loading.set(true);
    this.http
      .post<PatientPortalLogin>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.portalLogin}`, {
        clinicId: this.loginForm.clinicId,
        email: this.loginForm.email,
        password: this.loginForm.password,
      })
      .subscribe({
        next: (response) => {
          this.accessToken.set(response.accessToken);
          this.patient.set(response.patient);
          this.loading.set(false);
          this.loadRecords();
          this.loadTreatmentCharges();
        },
        error: () => this.loading.set(false),
      });
  }

  protected logout(): void {
    this.accessToken.set('');
    this.patient.set(null);
    this.records.set([]);
    this.treatmentCharges.set([]);
    this.selectedRecordIds.set(new Set());
  }

  protected toggleRecordSelection(recordId: string, event: Event): void {
    const selected = new Set(this.selectedRecordIds());
    if ((event.target as HTMLInputElement).checked) selected.add(recordId);
    else selected.delete(recordId);
    this.selectedRecordIds.set(selected);
  }

  protected downloadRecord(record: HealthRecord): void {
    this.http
      .get(`${this.baseUrl}/${API_ENDPOINTS.healthcare.portalRecords}/${record.id}/download`, {
        headers: this.authorizationHeaders(),
        responseType: 'blob',
      })
      .subscribe((blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `record-${record.id}.json`;
        link.click();
        URL.revokeObjectURL(url);
      });
  }

  protected startTreatmentPayment(charge: PatientPortalTreatmentCharge): void {
    if (!charge.paymentEnabled || this.payingChargeId()) return;
    this.payingChargeId.set(charge.chargeEntryId);
    this.http
      .post<TreatmentPaymentOrder>(
        `${this.baseUrl}/${API_ENDPOINTS.billing.patientPortalPaymentOrder}`,
        { chargeEntryId: charge.chargeEntryId },
        { headers: this.authorizationHeaders() },
      )
      .subscribe({
        next: (order) => {
          this.payingChargeId.set('');
          const checkout = new Razorpay({
            key: order.keyId,
            amount: order.amount,
            currency: order.currency,
            name: 'DentalPilot AI',
            description: 'Dental treatment payment',
            order_id: order.orderId,
            prefill: {
              name: this.patient()?.fullName,
              email: this.patient()?.email,
            },
            theme: { color: '#0f766e' },
            handler: (response) => this.verifyTreatmentPayment(response),
          });
          checkout.on('payment.failed', (failure) => {
            this.notifications.error(failure.error.description || 'Treatment payment failed.');
          });
          checkout.open();
        },
        error: () => this.payingChargeId.set(''),
      });
  }

  protected shareRecords(): void {
    const recordIds = Array.from(this.selectedRecordIds());
    if (!recordIds.length || !this.shareForm.recipientName.trim()) {
      this.notifications.error('Enter a recipient and at least one record ID to share.');
      return;
    }
    const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
    this.http
      .post<PatientPortalShare>(
        `${this.baseUrl}/${API_ENDPOINTS.healthcare.portalShares}`,
        {
          purpose: this.shareForm.purpose,
          recipientName: this.shareForm.recipientName,
          recordIds,
          scope: ['view'],
          expiresAt,
        },
        { headers: this.authorizationHeaders() },
      )
      .subscribe((share) => {
        this.shareLink.set(
          `${window.location.origin}/patient-portal?share=${encodeURIComponent(share.shareToken)}`,
        );
        this.selectedRecordIds.set(new Set());
        this.notifications.success('Secure, expiring share link created.');
      });
  }

  private loadRecords(): void {
    this.http
      .get<HealthRecord[]>(`${this.baseUrl}/${API_ENDPOINTS.healthcare.portalRecords}`, {
        headers: this.authorizationHeaders(),
      })
      .subscribe((records) => this.records.set(records));
  }

  private loadTreatmentCharges(): void {
    this.http
      .get<PatientPortalTreatmentCharge[]>(
        `${this.baseUrl}/${API_ENDPOINTS.billing.patientPortalCharges}`,
        { headers: this.authorizationHeaders() },
      )
      .subscribe((charges) => this.treatmentCharges.set(charges));
  }

  private verifyTreatmentPayment(response: {
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }): void {
    this.http
      .post<TreatmentPaymentVerify>(
        `${this.baseUrl}/${API_ENDPOINTS.billing.verifyPatientPortalPayment}`,
        {
          razorpayOrderId: response.razorpay_order_id,
          razorpayPaymentId: response.razorpay_payment_id,
          razorpaySignature: response.razorpay_signature,
        },
        { headers: this.authorizationHeaders() },
      )
      .subscribe({
        next: () => {
          this.notifications.success('Treatment payment confirmed.');
          this.loadTreatmentCharges();
        },
        error: () =>
          this.notifications.error(
            'Payment confirmation is pending. If you were charged, do not retry; contact the clinic for reconciliation.',
          ),
      });
  }

  private loadSharedRecords(token: string): void {
    this.http
      .get<PatientPortalSharedRecords>(
        `${this.baseUrl}/${API_ENDPOINTS.healthcare.portalShares}/${encodeURIComponent(token)}`,
      )
      .subscribe((result) => this.shared.set(result));
  }

  private authorizationHeaders(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.accessToken()}` });
  }
}
