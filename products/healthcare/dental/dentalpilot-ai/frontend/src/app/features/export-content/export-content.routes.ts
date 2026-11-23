import { Routes } from '@angular/router';

export const EXPORT_CONTENT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./export-content').then((m) => m.ExportContent),
  },
];
