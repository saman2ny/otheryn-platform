import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { catchError, finalize, of } from 'rxjs';
import { NotificationService } from '../../core/services/notification.service';
import { AuthService } from '../../core/services/auth.service';
import { ClinicProfile } from '../../core/models/clinic.model';
import { formFieldClass } from '../../shared/forms/form-field-class';
import { PageHeader } from '../../shared/ui/page-header/page-header';
import { ClinicProfileService } from './clinic-profile.service';

@Component({
  selector: 'dp-clinic-profile',
  imports: [ReactiveFormsModule, PageHeader],
  templateUrl: './clinic-profile.html',
})
export class ClinicProfilePage {
  protected readonly inputClass = formFieldClass;

  private readonly fb = inject(FormBuilder);
  private readonly clinicProfileService = inject(ClinicProfileService);
  private readonly notifications = inject(NotificationService);
  private readonly auth = inject(AuthService);

  protected readonly canManage = this.auth.canManageClinic;
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);

  protected readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    specialty: ['general-dentistry' as ClinicProfile['specialty'], Validators.required],
    aboutText: [''],
    website: [''],
    phone: ['', Validators.required],
    address: ['', Validators.required],
    city: ['', Validators.required],
    country: ['', Validators.required],
    brandTone: ['professional' as ClinicProfile['brandTone'], Validators.required],
    targetAudience: [''],
  });

  constructor() {
    this.clinicProfileService
      .getProfile()
      .pipe(
        catchError(() => of(null)),
        finalize(() => this.loading.set(false)),
      )
      .subscribe((profile) => {
        if (profile) {
          const { id, ...editable } = profile;
          this.form.patchValue(editable);
        }
        if (!this.canManage()) {
          this.form.disable();
        }
      });
  }

  protected save(): void {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving.set(true);
    this.clinicProfileService
      .updateProfile(this.form.getRawValue())
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: () => this.notifications.success('Clinic profile saved.'),
      });
  }
}
