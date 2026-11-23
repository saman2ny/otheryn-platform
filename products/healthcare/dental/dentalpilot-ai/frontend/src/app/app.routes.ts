import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { guestGuard } from './core/guards/guest.guard';

export const routes: Routes = [
  {
    path: 'patient-portal',
    loadComponent: () =>
      import('./features/patient-portal/patient-portal').then((m) => m.PatientPortal),
  },
  {
    path: 'staff-invitation',
    loadComponent: () =>
      import('./features/staff-invitation/staff-invitation').then((m) => m.StaffInvitationPage),
  },
  {
    path: 'auth',
    canActivate: [guestGuard],
    loadComponent: () => import('./layout/auth-layout/auth-layout').then((m) => m.AuthLayout),
    loadChildren: () => import('./features/auth/auth.routes').then((m) => m.AUTH_ROUTES),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layout/shell/shell').then((m) => m.Shell),
    children: [
      {
        path: 'dashboard',
        loadChildren: () =>
          import('./features/dashboard/dashboard.routes').then((m) => m.DASHBOARD_ROUTES),
      },
      {
        path: 'clinic-profile',
        loadChildren: () =>
          import('./features/clinic-profile/clinic-profile.routes').then(
            (m) => m.CLINIC_PROFILE_ROUTES,
          ),
      },
      {
        path: 'content-generator',
        loadChildren: () =>
          import('./features/content-generator/content-generator.routes').then(
            (m) => m.CONTENT_GENERATOR_ROUTES,
          ),
      },
      {
        path: 'content-calendar',
        loadChildren: () =>
          import('./features/content-calendar/content-calendar.routes').then(
            (m) => m.CONTENT_CALENDAR_ROUTES,
          ),
      },
      {
        path: 'growth-os',
        loadComponent: () =>
          import('./features/clinic-growth-os/clinic-growth-os').then((m) => m.ClinicGrowthOs),
      },
      {
        path: 'dental-operations',
        loadComponent: () =>
          import('./features/dental-operations/dental-operations').then(
            (m) => m.DentalOperations,
          ),
      },
      {
        path: 'organization-management',
        loadComponent: () =>
          import('./features/organization-management/organization-management').then(
            (m) => m.OrganizationManagement,
          ),
      },
      {
        path: 'export-content',
        loadChildren: () =>
          import('./features/export-content/export-content.routes').then(
            (m) => m.EXPORT_CONTENT_ROUTES,
          ),
      },
      {
        path: 'billing',
        loadChildren: () =>
          import('./features/billing/billing.routes').then((m) => m.BILLING_ROUTES),
      },
      {
        path: 'dentalpilot-workflows',
        loadChildren: () =>
          import('./features/dentalpilot-workflows/dentalpilot-workflows.routes').then(
            (m) => m.DENTALPILOT_WORKFLOWS_ROUTES,
          ),
      },
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
    ],
  },
  { path: '**', redirectTo: '' },
];
