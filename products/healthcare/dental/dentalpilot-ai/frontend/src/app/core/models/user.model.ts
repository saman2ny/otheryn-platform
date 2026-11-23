export type PlanTier = 'free' | 'starter' | 'professional' | 'enterprise';
export type UserRole = 'super_admin' | 'owner' | 'staff';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  clinicId: string;
  clinicName: string;
  planTier: PlanTier;
  createdAt: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface AuthResponse extends AuthTokens {
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  fullName: string;
  clinicName: string;
  email: string;
  password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}
