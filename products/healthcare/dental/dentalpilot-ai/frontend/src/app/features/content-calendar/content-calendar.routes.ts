import { Routes } from '@angular/router';

export const CONTENT_CALENDAR_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./content-calendar').then((m) => m.ContentCalendar),
  },
];
