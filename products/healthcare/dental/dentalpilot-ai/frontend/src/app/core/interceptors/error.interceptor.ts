import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { NotificationService } from '../services/notification.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const notifications = inject(NotificationService);
  const authService = inject(AuthService);

  return next(req).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse) {
        const isPatientPortalRequest = req.url.includes('/patient-portal/');
        if (error.status === 401 && !isPatientPortalRequest) {
          authService.logout();
        } else if (error.status === 0) {
          notifications.error('Unable to reach the server. Check your connection.');
        } else {
          const response = error.error as { message?: string; detail?: string } | null;
          const message = response?.detail ?? response?.message;
          notifications.error(message ?? 'Something went wrong. Please try again.');
        }
      }
      return throwError(() => error);
    }),
  );
};
