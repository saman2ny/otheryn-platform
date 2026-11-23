import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, of, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../constants/api-endpoints.const';
import {
  AuthResponse,
  ForgotPasswordRequest,
  LoginRequest,
  RegisterRequest,
  User,
} from '../models/user.model';
import { TokenStorageService } from './token-storage.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly tokenStorage = inject(TokenStorageService);
  private readonly router = inject(Router);
  private readonly baseUrl = environment.apiBaseUrl;

  private readonly currentUserSignal = signal<User | null>(null);
  private readonly sessionRestoredSignal = signal(false);

  readonly currentUser = this.currentUserSignal.asReadonly();
  readonly sessionRestored = this.sessionRestoredSignal.asReadonly();
  readonly isAuthenticated = computed(() => this.currentUserSignal() !== null);

  /** Owner or super_admin — can manage clinic profile and billing. Staff cannot. */
  readonly canManageClinic = computed(() => {
    const role = this.currentUserSignal()?.role;
    return role === 'owner' || role === 'super_admin';
  });

  login(request: LoginRequest): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(`${this.baseUrl}/${API_ENDPOINTS.auth.login}`, request)
      .pipe(tap((response) => this.applySession(response)));
  }

  register(request: RegisterRequest): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(`${this.baseUrl}/${API_ENDPOINTS.auth.register}`, request)
      .pipe(tap((response) => this.applySession(response)));
  }

  forgotPassword(request: ForgotPasswordRequest): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/${API_ENDPOINTS.auth.forgotPassword}`, request);
  }

  logout(): void {
    this.tokenStorage.clear();
    this.currentUserSignal.set(null);
    this.router.navigate(['/auth/login']);
  }

  /** Called once during app bootstrap to rehydrate the session from a stored token. */
  restoreSession(): Observable<User | null> {
    if (!this.tokenStorage.getAccessToken()) {
      this.sessionRestoredSignal.set(true);
      return of(null);
    }

    return this.http.get<User>(`${this.baseUrl}/${API_ENDPOINTS.auth.me}`).pipe(
      tap((user) => this.currentUserSignal.set(user)),
      catchError(() => {
        this.tokenStorage.clear();
        this.currentUserSignal.set(null);
        return of(null);
      }),
      tap(() => this.sessionRestoredSignal.set(true)),
    );
  }

  private applySession(response: AuthResponse): void {
    this.tokenStorage.setTokens(response);
    this.currentUserSignal.set(response.user);
  }
}
