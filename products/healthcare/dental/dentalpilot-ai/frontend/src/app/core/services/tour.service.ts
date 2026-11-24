import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import Shepherd, { Tour } from 'shepherd.js';
import { AuthService } from './auth.service';

export type TourRole = 'super_admin' | 'owner';

interface TourStep {
  id: string;
  title: string;
  text: string;
  route?: string;
  selector?: string;
}

const TOUR_VERSION = '1';

const SUPER_ADMIN_TOUR: TourStep[] = [
  {
    id: 'sa-dashboard',
    title: 'Welcome to DentalPilot AI',
    text: 'This is your practice dashboard. Use the sidebar to move between clinical, patient and administrative tools.',
    route: '/dashboard',
    selector: '.dp-sidebar',
  },
  {
    id: 'sa-directory',
    title: 'Patient directory',
    text: 'Open Patients & CRM to search, filter and review patient records across your authorized clinics.',
    route: '/dentalpilot-workflows',
    selector: 'a[href="/dentalpilot-workflows"]',
  },
  {
    id: 'sa-register',
    title: 'Register a patient',
    text: 'Use the registration form to add a patient. Required fields are validated on the server.',
    route: '/dentalpilot-workflows',
    selector: 'input[name="fullName"]',
  },
  {
    id: 'sa-search',
    title: 'Search and filter',
    text: 'Search by name, email or phone. Results are paginated and scoped to your role.',
    route: '/dentalpilot-workflows',
    selector: 'input[name="patientSearch"]',
  },
  {
    id: 'sa-edit',
    title: 'Edit patient information',
    text: 'Select a patient and choose Edit to update demographics and contact details.',
    route: '/dentalpilot-workflows',
    selector: '.dp-page-header',
  },
  {
    id: 'sa-medical',
    title: 'Medical history',
    text: 'Record conditions, allergies, medications and surgeries in the medical history fields.',
    route: '/dentalpilot-workflows',
    selector: 'input[name="medConditions"]',
  },
  {
    id: 'sa-dental',
    title: 'Dental history',
    text: 'Record previous treatments, conditions and patient concerns.',
    route: '/dentalpilot-workflows',
    selector: 'input[name="dentalTreatments"]',
  },
  {
    id: 'sa-emergency',
    title: 'Emergency contacts',
    text: 'Add an emergency contact with name, relationship and phone.',
    route: '/dentalpilot-workflows',
    selector: 'input[name="ecName"]',
  },
  {
    id: 'sa-duplicates',
    title: 'Duplicate detection',
    text: 'Use Check duplicates before registering to spot possible matches. No automatic merge is performed.',
    route: '/dentalpilot-workflows',
  },
  {
    id: 'sa-revisions',
    title: 'Revision history',
    text: 'Choose History on a patient to review previous versions and who changed them.',
    route: '/dentalpilot-workflows',
  },
  {
    id: 'sa-filters',
    title: 'Clinic and branch filters',
    text: 'Use the clinic and branch selectors to scope the directory to the area you manage.',
    route: '/dentalpilot-workflows',
  },
  {
    id: 'sa-audit',
    title: 'Patient audit information',
    text: 'Open Dental Analytics or the audit views to review patient-related activity and exports.',
    route: '/dentalpilot-workflows',
  },
];

const OWNER_TOUR: TourStep[] = [
  {
    id: 'owner-dashboard',
    title: 'Welcome to your clinic dashboard',
    text: 'This is your clinic overview. The sidebar is your primary navigation.',
    route: '/dashboard',
    selector: '.dp-sidebar',
  },
  {
    id: 'owner-directory',
    title: 'Patient directory',
    text: 'Open Patients & CRM to see patients in your clinic and branches.',
    route: '/dentalpilot-workflows',
    selector: 'a[href="/dentalpilot-workflows"]',
  },
  {
    id: 'owner-register',
    title: 'Register a patient',
    text: 'Add a patient with the registration form. Required fields are validated on the server.',
    route: '/dentalpilot-workflows',
    selector: 'input[name="fullName"]',
  },
  {
    id: 'owner-profile',
    title: 'Patient profile',
    text: 'Search and open a patient to review their record and history.',
    route: '/dentalpilot-workflows',
    selector: 'input[name="patientSearch"]',
  },
  {
    id: 'owner-edit',
    title: 'Edit patient information',
    text: 'Choose Edit on a patient to update demographics and contact details.',
    route: '/dentalpilot-workflows',
    selector: '.dp-page-header',
  },
  {
    id: 'owner-medical',
    title: 'Medical history',
    text: 'Record conditions, allergies, medications and surgeries.',
    route: '/dentalpilot-workflows',
    selector: 'input[name="medConditions"]',
  },
  {
    id: 'owner-dental',
    title: 'Dental history',
    text: 'Record previous treatments, conditions and concerns.',
    route: '/dentalpilot-workflows',
    selector: 'input[name="dentalTreatments"]',
  },
  {
    id: 'owner-emergency',
    title: 'Emergency contacts',
    text: 'Add an emergency contact with name, relationship and phone.',
    route: '/dentalpilot-workflows',
    selector: 'input[name="ecName"]',
  },
  {
    id: 'owner-duplicates',
    title: 'Duplicate detection',
    text: 'Check for possible duplicates before registering. No automatic merge is performed.',
    route: '/dentalpilot-workflows',
  },
  {
    id: 'owner-revisions',
    title: 'Revision history',
    text: 'Choose History on a patient to review previous versions.',
    route: '/dentalpilot-workflows',
  },
  {
    id: 'owner-associations',
    title: 'Treatment and clinical records',
    text: 'Use the Treatment Journey and Clinical Records modules to coordinate care for the same patient.',
    route: '/dentalpilot-workflows',
  },
  {
    id: 'owner-consent',
    title: 'Consent and Patient Passport',
    text: 'Review consent and share records through the Patient Passport and consent tools.',
    route: '/dentalpilot-workflows',
  },
];

const TOURS: Record<TourRole, TourStep[]> = {
  super_admin: SUPER_ADMIN_TOUR,
  owner: OWNER_TOUR,
};

@Injectable({ providedIn: 'root' })
export class TourService {
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);
  private tour: Tour | null = null;

  private key(role: TourRole, suffix: string): string {
    return `dp_tour_${role}_${TOUR_VERSION}_${suffix}`;
  }

  private isCompleted(role: TourRole): boolean {
    return localStorage.getItem(this.key(role, 'completed')) === '1';
  }

  private isSkipped(role: TourRole): boolean {
    return localStorage.getItem(this.key(role, 'skipped')) === '1';
  }

  private markCompleted(role: TourRole): void {
    localStorage.setItem(this.key(role, 'completed'), '1');
    localStorage.removeItem(this.key(role, 'skipped'));
  }

  private markSkipped(role: TourRole): void {
    localStorage.setItem(this.key(role, 'skipped'), '1');
  }

  private resolveRole(role?: TourRole): TourRole | null {
    if (role === 'super_admin' || role === 'owner') return role;
    const current = this.auth.currentUser()?.role;
    if (current === 'super_admin') return 'super_admin';
    if (current === 'owner') return 'owner';
    return null;
  }

  maybeStart(): void {
    const role = this.resolveRole();
    if (!role || this.isCompleted(role) || this.isSkipped(role)) return;
    this.start(role);
  }

  start(role?: TourRole): void {
    const resolved = this.resolveRole(role);
    if (!resolved) return;
    if (this.tour) this.tour.cancel();

    const tour = new Shepherd.Tour({
      useModalOverlay: true,
      exitOnEsc: true,
      defaultStepOptions: {
        classes: 'dp-tour',
        scrollTo: true,
        cancelIcon: { enabled: true },
      },
    });

    for (const step of TOURS[resolved]) {
      tour.addStep({
        id: step.id,
        title: step.title,
        text: step.text,
        attachTo: step.selector ? { element: step.selector, on: 'bottom' } : undefined,
      });
    }

    tour.on('step-change', (step: unknown) => {
      const id = (step as { id?: string })?.id ?? '';
      const target = id.endsWith('dashboard') ? '/dashboard' : '/dentalpilot-workflows';
      if (this.router.url !== target) {
        void this.router.navigateByUrl(target);
      }
    });

    tour.on('complete', () => this.markCompleted(resolved));
    tour.on('cancel', () => this.markSkipped(resolved));

    this.tour = tour;
    void tour.start();
  }

  restart(role?: TourRole): void {
    const resolved = this.resolveRole(role);
    if (!resolved) return;
    localStorage.removeItem(this.key(resolved, 'completed'));
    localStorage.removeItem(this.key(resolved, 'skipped'));
    this.start(resolved);
  }
}