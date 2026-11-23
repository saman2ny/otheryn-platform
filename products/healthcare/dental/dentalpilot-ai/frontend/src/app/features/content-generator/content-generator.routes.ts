import { Routes } from '@angular/router';

export const CONTENT_GENERATOR_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./content-generator').then((m) => m.ContentGenerator),
  },
];
