import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';
import { NotificationService } from '../../core/services/notification.service';

@Component({
  selector: 'dp-staff-invitation',
  imports: [FormsModule],
  templateUrl: './staff-invitation.html',
})
export class StaffInvitationPage {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly notifications = inject(NotificationService);
  private readonly baseUrl = environment.apiBaseUrl;

  protected readonly token = signal('');
  protected readonly password = signal('');
  protected readonly accepted = signal(false);
  protected readonly saving = signal(false);

  constructor() {
    const token = this.route.snapshot.queryParamMap.get('token');
    if (token) this.token.set(token);
  }

  protected updateToken(event: Event): void {
    this.token.set((event.target as HTMLInputElement).value);
  }

  protected acceptInvitation(): void {
    if (!this.token() || this.password().length < 12) {
      this.notifications.error(
        'Enter the invitation token and a password of at least 12 characters.',
      );
      return;
    }
    this.saving.set(true);
    this.http
      .post<void>(`${this.baseUrl}/${API_ENDPOINTS.clinic.acceptStaffInvitation}`, {
        invitationToken: this.token(),
        password: this.password(),
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.accepted.set(true);
          this.notifications.success('Invitation accepted. You can now sign in.');
        },
        error: () => this.saving.set(false),
      });
  }
}
