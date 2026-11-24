import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import Shepherd, { Tour } from 'shepherd.js';
import type { StepOptions } from 'shepherd.js';
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
    selector: 'dp-page-header',
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
    selector: 'dp-page-header',
  },
  {
    id: 'sa-revisions',
    title: 'Revision history',
    text: 'Choose History on a patient to review previous versions and who changed them.',
    route: '/dentalpilot-workflows',
    selector: 'dp-page-header',
  },
  {
    id: 'sa-filters',
    title: 'Clinic and branch filters',
    text: 'Use the clinic and branch selectors to scope the directory to the area you manage.',
    route: '/dentalpilot-workflows',
    selector: 'dp-page-header',
  },
  {
    id: 'sa-audit',
    title: 'Patient audit information',
    text: 'Open Dental Analytics or the audit views to review patient-related activity and exports.',
    route: '/dentalpilot-workflows',
    selector: 'dp-page-header',
  },
  {
    id: 'sa-organizations',
    title: 'Clinic group',
    text: 'Manage multi-clinic organizations, members and invitations.',
    route: '/organization-management',
    selector: 'dp-page-header',
  },
  {
    id: 'sa-content',
    title: 'AI content studio',
    text: 'Generate marketing content with Groq and review drafts.',
    route: '/content-generator',
    selector: 'dp-page-header',
  },
  {
    id: 'sa-calendar',
    title: 'Content calendar',
    text: 'Schedule and review upcoming content.',
    route: '/content-calendar',
    selector: 'dp-page-header',
  },
  {
    id: 'sa-growth',
    title: 'Growth OS',
    text: 'Review local listings, campaigns and reviews.',
    route: '/growth-os',
    selector: 'dp-page-header',
  },
  {
    id: 'sa-export',
    title: 'Export library',
    text: 'Create and download CSV/PDF/PNG exports.',
    route: '/export-content',
    selector: 'dp-page-header',
  },
  {
    id: 'sa-billing',
    title: 'Plan and billing',
    text: 'Manage the clinic subscription and invoices.',
    route: '/billing',
    selector: 'dp-page-header',
  },
  {
    id: 'sa-operations',
    title: 'Dental operations',
    text: 'Coordinate cases, equipment, sterilisation and clinical notes.',
    route: '/dental-operations',
    selector: 'dp-page-header',
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
    selector: 'dp-page-header',
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
    selector: 'dp-page-header',
  },
  {
    id: 'owner-revisions',
    title: 'Revision history',
    text: 'Choose History on a patient to review previous versions.',
    route: '/dentalpilot-workflows',
    selector: 'dp-page-header',
  },
  {
    id: 'owner-associations',
    title: 'Treatment and clinical records',
    text: 'Use the Treatment Journey and Clinical Records modules to coordinate care for the same patient.',
    route: '/dentalpilot-workflows',
    selector: 'dp-page-header',
  },
  {
    id: 'owner-consent',
    title: 'Consent and Patient Passport',
    text: 'Review consent and share records through the Patient Passport and consent tools.',
    route: '/dentalpilot-workflows',
    selector: 'dp-page-header',
  },
  {
    id: 'owner-organizations',
    title: 'Clinic group',
    text: 'Manage multi-clinic organizations, members and invitations.',
    route: '/organization-management',
    selector: 'dp-page-header',
  },
  {
    id: 'owner-content',
    title: 'AI content studio',
    text: 'Generate marketing content with Groq and review drafts.',
    route: '/content-generator',
    selector: 'dp-page-header',
  },
  {
    id: 'owner-calendar',
    title: 'Content calendar',
    text: 'Schedule and review upcoming content.',
    route: '/content-calendar',
    selector: 'dp-page-header',
  },
  {
    id: 'owner-growth',
    title: 'Growth OS',
    text: 'Review local listings, campaigns and reviews.',
    route: '/growth-os',
    selector: 'dp-page-header',
  },
  {
    id: 'owner-export',
    title: 'Export library',
    text: 'Create and download CSV/PDF/PNG exports.',
    route: '/export-content',
    selector: 'dp-page-header',
  },
  {
    id: 'owner-billing',
    title: 'Plan and billing',
    text: 'Manage the clinic subscription and invoices.',
    route: '/billing',
    selector: 'dp-page-header',
  },
  {
    id: 'owner-operations',
    title: 'Dental operations',
    text: 'Coordinate cases, equipment, sterilisation and clinical notes.',
    route: '/dental-operations',
    selector: 'dp-page-header',
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
  private readonly onViewportChange = () => {
    const step = this.tour?.getCurrentStep();
    if (step) {
      step.updateStepOptions({});
    }
  };

  private currentUser(): { id: string; role: string } | null {
    const user = this.auth.currentUser();
    if (!user?.id) return null;
    return { id: user.id, role: user.role };
  }

  private key(userId: string, role: TourRole, suffix: string): string {
    return `dp_tour_${userId}_${role}_${TOUR_VERSION}_${suffix}`;
  }

  private isCompleted(userId: string, role: TourRole): boolean {
    return localStorage.getItem(this.key(userId, role, 'completed')) === '1';
  }

  private isSkipped(userId: string, role: TourRole): boolean {
    return localStorage.getItem(this.key(userId, role, 'skipped')) === '1';
  }

  private markCompleted(userId: string, role: TourRole): void {
    localStorage.setItem(this.key(userId, role, 'completed'), '1');
    localStorage.removeItem(this.key(userId, role, 'skipped'));
  }

  private markSkipped(userId: string, role: TourRole): void {
    localStorage.setItem(this.key(userId, role, 'skipped'), '1');
  }

  private resolveRole(role?: TourRole): TourRole | null {
    if (role === 'super_admin' || role === 'owner') return role;
    const current = this.auth.currentUser()?.role;
    if (current === 'super_admin') return 'super_admin';
    if (current === 'owner') return 'owner';
    return null;
  }

  maybeStart(): void {
    const user = this.currentUser();
    const role = this.resolveRole();
    if (!user || !role) return;
    if (this.isCompleted(user.id, role) || this.isSkipped(user.id, role)) return;
    this.start(role);
  }

  private async ensurePatientForEditForm(): Promise<boolean> {
    const existingEdit = Array.from(document.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Edit',
    );
    if (existingEdit instanceof HTMLButtonElement) return true;

    const fullName = document.querySelector('input[name="fullName"]') as HTMLInputElement | null;
    const email = document.querySelector('input[name="email"]') as HTMLInputElement | null;
    const addButton = Array.from(document.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Add patient',
    );
    if (!fullName || !addButton) return false;

    fullName.value = 'Tour Demo Patient';
    fullName.dispatchEvent(new Event('input', { bubbles: true }));
    if (email) {
      email.value = `tour.demo+${Date.now()}@example.com`;
      email.dispatchEvent(new Event('input', { bubbles: true }));
    }
    (addButton as HTMLButtonElement).click();
    await new Promise<void>((resolve) => setTimeout(resolve, 800));
    return Array.from(document.querySelectorAll('button')).some(
      (button) => button.textContent?.trim() === 'Edit',
    );
  }

  private isEditFormSelector(selector: string): boolean {
    return ['medConditions', 'dentalTreatments', 'ecName'].some((name) =>
      selector.includes(`name="${name}"`),
    );
  }

  private openFirstPatientEdit(): void {
    const editButton = Array.from(document.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Edit',
    );
    if (editButton instanceof HTMLButtonElement) {
      editButton.click();
    }
  }

  private placementFor(selector?: string): 'top' | 'bottom' | 'left' | 'right' {
    if (!selector) return 'bottom';
    const element = document.querySelector(selector);
    if (!(element instanceof HTMLElement)) return 'bottom';
    const rect = element.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const space = {
      top: rect.top,
      bottom: viewportHeight - rect.bottom,
      left: rect.left,
      right: viewportWidth - rect.right,
    };
    const placements: Array<'bottom' | 'top' | 'right' | 'left'> = ['bottom', 'top', 'right', 'left'];
    return placements.reduce((best, placement) =>
      space[placement] > space[best] ? placement : best,
    );
  }

  private async waitForSelector(selector: string, timeoutMs = 3000): Promise<HTMLElement | null> {
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      const element = document.querySelector(selector);
      if (element instanceof HTMLElement) return element;
      await new Promise<void>((resolve) => setTimeout(resolve, 100));
    }
    const element = document.querySelector(selector);
    return element instanceof HTMLElement ? element : null;
  }

  private addViewportListeners(): void {
    window.addEventListener('resize', this.onViewportChange);
    window.addEventListener('orientationchange', this.onViewportChange);
  }

  private removeViewportListeners(): void {
    window.removeEventListener('resize', this.onViewportChange);
    window.removeEventListener('orientationchange', this.onViewportChange);
  }

  start(role?: TourRole): void {
    const user = this.currentUser();
    const resolved = this.resolveRole(role);
    if (!user || !resolved) return;
    if (this.tour) {
      this.removeViewportListeners();
      this.tour.cancel();
    }

    const tour = new Shepherd.Tour({
      useModalOverlay: true,
      exitOnEsc: true,
      defaultStepOptions: {
        classes: 'dp-tour',
        scrollTo: { behavior: 'smooth', block: 'center' },
        cancelIcon: { enabled: true },
      },
    });

    const steps = TOURS[resolved];
    steps.forEach((step, index) => {
      const isLast = index === steps.length - 1;
      const buttons = [
        ...(index > 0
          ? [{ text: 'Previous', action: tour.back, classes: 'shepherd-button-secondary' }]
          : []),
        {
          text: isLast ? 'Finish' : 'Next',
          action: isLast ? tour.complete : tour.next,
          classes: 'shepherd-button-primary',
        },
        { text: 'Skip tour', action: tour.cancel, classes: 'shepherd-button-secondary' },
      ];

      const config: StepOptions & { beforeShowPromise?: () => Promise<void> } = {
        id: step.id,
        title: `Step ${index + 1} of ${steps.length} — ${step.title}`,
        text: step.text,
        attachTo: step.selector
          ? { element: step.selector, on: this.placementFor(step.selector) }
          : undefined,
        buttons,
        beforeShowPromise: async () => {
          if (step.route && this.router.url !== step.route) {
            await this.router.navigateByUrl(step.route);
            await new Promise<void>((resolve) => setTimeout(resolve, 150));
          }
          if (!step.selector) return;

          let target = await this.waitForSelector(step.selector, 3000);
          if (!target && this.isEditFormSelector(step.selector)) {
            await this.ensurePatientForEditForm();
            this.openFirstPatientEdit();
            target = await this.waitForSelector(step.selector, 3000);
          }

          const current = tour.getCurrentStep();
          if (!target) {
            console.warn(
              `[DentalPilot tour] Missing target for step "${step.id}": ${step.selector}`,
            );
            if (current) current.updateStepOptions({ attachTo: undefined });
            return;
          }

          if (current) {
            current.updateStepOptions({
              attachTo: { element: step.selector, on: this.placementFor(step.selector) },
            });
          }
        },
      };

      tour.addStep(config);
    });

    tour.on('complete', () => {
      this.removeViewportListeners();
      this.markCompleted(user.id, resolved);
    });
    tour.on('cancel', () => {
      this.removeViewportListeners();
      this.markSkipped(user.id, resolved);
    });

    this.tour = tour;
    this.addViewportListeners();
    void tour.start();
  }

  restart(role?: TourRole): void {
    const user = this.currentUser();
    const resolved = this.resolveRole(role);
    if (!user || !resolved) return;
    localStorage.removeItem(this.key(user.id, resolved, 'completed'));
    localStorage.removeItem(this.key(user.id, resolved, 'skipped'));
    this.start(resolved);
  }
}