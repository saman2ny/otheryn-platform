import { Routes } from '@angular/router';

export const DENTALPILOT_WORKFLOWS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./dentalpilot-workflows').then((m) => m.DentalPilotWorkflows),
  },
];
