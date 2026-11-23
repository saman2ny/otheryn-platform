import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { environment } from '../../../environments/environment';
import { TokenStorageService } from '../services/token-storage.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const tokenStorage = inject(TokenStorageService);
  const isApiRequest = req.url.startsWith(environment.apiBaseUrl);
  const isPatientPortalRequest = req.url.includes('/patient-portal/');
  const accessToken = tokenStorage.getAccessToken();

  if (!isApiRequest || !accessToken || isPatientPortalRequest || req.headers.has('Authorization')) {
    return next(req);
  }

  return next(
    req.clone({
      setHeaders: { Authorization: `Bearer ${accessToken}` },
    }),
  );
};
