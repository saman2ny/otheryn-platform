from datetime import datetime
from typing import Literal

from pydantic import EmailStr

from app.schemas.common import CamelModel

PlanTier = Literal["free", "starter", "professional", "enterprise"]
UserRole = Literal["super_admin", "owner", "staff"]


class User(CamelModel):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    clinic_id: str
    clinic_name: str
    plan_tier: PlanTier
    created_at: datetime


class AuthTokens(CamelModel):
    access_token: str
    refresh_token: str


class AuthResponse(AuthTokens):
    user: User


class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class RegisterRequest(CamelModel):
    full_name: str
    clinic_name: str
    email: EmailStr
    password: str


class ForgotPasswordRequest(CamelModel):
    email: EmailStr
