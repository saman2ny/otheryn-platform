import { Routes } from '@angular/router';

export const CLINIC_PROFILE_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./clinic-profile').then((m) => m.ClinicProfilePage),
  },
];
