from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.schemas.common import CamelModel

ClinicSpecialty = Literal[
    "general-dentistry", "orthodontics", "cosmetic-dentistry", "implants", "pediatric-dentistry"
]
BrandTone = Literal["friendly", "professional", "premium", "playful"]


class ClinicProfile(CamelModel):
    id: str
    name: str
    specialty: ClinicSpecialty
    about_text: str
    website: str | None = None
    phone: str
    address: str
    city: str
    country: str
    logo_url: str | None = None
    brand_tone: BrandTone
    target_audience: str


class UpdateClinicProfileRequest(CamelModel):
    name: str
    specialty: ClinicSpecialty
    about_text: str
    website: str | None = None
    phone: str
    address: str
    city: str
    country: str
    logo_url: str | None = None
    brand_tone: BrandTone
    target_audience: str


class ClinicClinicalAiSettingsUpdate(CamelModel):
    enabled: bool


class ClinicClinicalAiSettingsResponse(CamelModel):
    enabled: bool
    available: bool


class ClinicBranchCreate(CamelModel):
    name: str = Field(min_length=2, max_length=120)
    address: str = ""
    phone: str = ""


class ClinicBranchResponse(CamelModel):
    id: str
    clinic_id: str
    name: str
    address: str
    phone: str
    is_primary: bool
    created_at: datetime


class StaffInvitationCreate(CamelModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    branch_id: str


class StaffInvitationResponse(CamelModel):
    id: str
    email: EmailStr
    full_name: str
    branch_id: str
    invitation_token: str
    expires_at: datetime


class StaffInvitationAccept(CamelModel):
    invitation_token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=128)


class StaffMemberResponse(CamelModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    branch_id: str | None = None
    created_at: datetime


class OnboardingStep(CamelModel):
    id: str
    name: str
    description: str
    completed: bool
    required: bool
    order: int


class OnboardingStatus(CamelModel):
    current_step: int
    total_steps: int
    steps: list[OnboardingStep]
    profile_complete: bool
    branch_count: int
    staff_count: int
    subscription_active: bool
    onboarding_completed_at: datetime | None = None
    can_complete: bool
