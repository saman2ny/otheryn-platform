from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.schemas.common import CamelModel

OrganizationMemberRole = Literal[
    "organization-owner",
    "organization-admin",
    "reporting-only",
    "clinic-owner",
]


class OrganizationCreate(CamelModel):
    name: str = Field(min_length=2, max_length=160)


class OrganizationResponse(CamelModel):
    id: str
    name: str
    created_at: datetime
    clinic_count: int
    current_member_role: OrganizationMemberRole


class OrganizationInvitationCreate(CamelModel):
    email: EmailStr


class OrganizationInvitationResponse(CamelModel):
    id: str
    organization_id: str
    email: EmailStr
    invitation_token: str
    expires_at: datetime


class OrganizationInvitationAccept(CamelModel):
    invitation_token: str = Field(min_length=32, max_length=256)


class OrganizationFinancialSummary(CamelModel):
    currency: str
    clinic_count: int
    charges_value: float
    payments_received: float
    refunds_value: float
    net_collected: float
    outstanding_balance: float


class OrganizationClinicSummary(CamelModel):
    clinic_id: str
    clinic_name: str
    branch_count: int
    patient_count: int
    financials: list[OrganizationFinancialSummary] = Field(default_factory=list)


class OrganizationAnalytics(CamelModel):
    organization_id: str
    organization_name: str
    clinic_count: int
    branch_count: int
    patient_count: int
    open_treatment_stage_count: int
    completed_visit_count: int
    clinics: list[OrganizationClinicSummary]
    financials: list[OrganizationFinancialSummary]


class OrganizationMemberResponse(CamelModel):
    user_id: str
    clinic_id: str
    full_name: str
    email: EmailStr
    role: OrganizationMemberRole
    created_at: datetime


class OrganizationMemberRoleUpdate(CamelModel):
    role: Literal["organization-admin", "reporting-only"]
