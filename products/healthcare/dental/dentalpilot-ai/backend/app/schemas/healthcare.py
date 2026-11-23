from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import EmailStr, Field, model_validator, computed_field

from app.schemas.common import CamelModel


class PatientCreate(CamelModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = None
    date_of_birth: str | None = None
    external_reference: str | None = None
    branch_id: str | None = None
    consent_channel: Literal["email", "sms", "whatsapp", "phone"] = "email"


class PatientResponse(CamelModel):
    id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    date_of_birth: str | None = None
    external_reference: str | None = None
    branch_id: str | None = None
    consent_channel: str
    created_at: datetime


class PatientEnquiryCreate(CamelModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    source: str = Field(default="unspecified", min_length=1, max_length=120)
    requested_service: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=2000)
    branch_id: str | None = None

    @model_validator(mode="after")
    def require_contact_method(self):
        if not self.email and not (self.phone or "").strip():
            raise ValueError("Provide an email address or phone number.")
        return self


class PatientEnquiryUpdate(CamelModel):
    status: Literal["new", "contacted", "consultation-booked", "closed"]


class PatientEnquiryResponse(CamelModel):
    id: str
    branch_id: str
    patient_id: str | None = None
    full_name: str
    email: str | None = None
    phone: str | None = None
    source: str
    requested_service: str
    notes: str
    status: str
    created_at: datetime
    updated_at: datetime


class PatientCommunicationCreate(CamelModel):
    channel: Literal["email", "sms", "whatsapp", "phone", "in-person"]
    direction: Literal["inbound", "outbound"]
    subject: str | None = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    template_id: str | None = None
    # Backward compatibility alias
    summary: str | None = Field(default=None, max_length=2000, validation_alias="summary")

    @model_validator(mode="before")
    @classmethod
    def _handle_summary_alias(cls, data: dict) -> dict:
        if isinstance(data, dict) and "summary" in data and "body" not in data:
            data["body"] = data.pop("summary")
        return data


class PatientCommunicationResponse(CamelModel):
    id: str
    patient_id: str
    channel: str
    direction: str
    subject: str | None = None
    body: str
    template_id: str | None = None
    status: str
    external_id: str | None = None
    error_message: str | None = None
    actor_id: str
    created_at: datetime
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None

    @computed_field
    @property
    def summary(self) -> str:
        """Backward compatibility property."""
        return self.body


class PatientEmailCreate(CamelModel):
    subject: str = Field(min_length=3, max_length=200)
    body_text: str = Field(min_length=1, max_length=10000)
    consent_confirmed: bool


class EmailOutboxResponse(CamelModel):
    id: str
    status: str
    recipient_email: str
    subject: str
    available_at: datetime
    sent_at: datetime | None = None
    attempt_count: int
    last_error: str | None = None
    created_at: datetime


class PatientVisitCreate(CamelModel):
    patient_id: str
    branch_id: str | None = None
    visit_type: Literal["consultation", "treatment", "hygiene", "other"]
    status: Literal["scheduled", "completed", "cancelled", "no-show"] = "scheduled"
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_visit_times(self):
        if self.scheduled_at and self.scheduled_at.tzinfo is None:
            raise ValueError("Scheduled visit time must include a timezone.")
        if self.completed_at and self.completed_at.tzinfo is None:
            raise ValueError("Completed visit time must include a timezone.")
        if self.status == "scheduled" and self.scheduled_at is None:
            raise ValueError("Scheduled visits require an appointment time.")
        if self.status == "completed" and self.completed_at is None:
            raise ValueError("Completed visits require a completion time.")
        return self


class PatientVisitResponse(CamelModel):
    id: str
    patient_id: str
    branch_id: str | None = None
    visit_type: str
    status: str
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str
    actor_id: str
    created_at: datetime


class TreatmentLedgerEntryCreate(CamelModel):
    patient_id: str
    branch_id: str | None = None
    stage_id: str | None = None
    charge_entry_id: str | None = None
    entry_type: Literal["charge", "payment", "refund"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="INR", pattern="^[A-Z]{3}$")
    method: Literal["cash", "card", "bank-transfer", "insurance", "razorpay", "other"] = "other"
    reference: str = Field(default="", max_length=160)
    notes: str = Field(default="", max_length=2000)


class TreatmentLedgerEntryResponse(CamelModel):
    id: str
    patient_id: str
    branch_id: str | None = None
    stage_id: str | None = None
    charge_entry_id: str | None = None
    entry_type: str
    amount: float
    currency: str
    method: str
    reference: str
    notes: str
    actor_id: str
    created_at: datetime


InsuranceClaimStatus = Literal[
    "draft",
    "submitted",
    "in-review",
    "approved",
    "partially-approved",
    "partially-paid",
    "paid",
    "denied",
    "cancelled",
]


class InsuranceClaimCreate(CamelModel):
    patient_id: str
    charge_entry_id: str | None = None
    supporting_record_id: str | None = None
    payer_name: str = Field(min_length=2, max_length=160)
    claim_number: str = Field(default="", max_length=120)
    billed_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="INR", pattern="^[A-Z]{3}$")
    notes: str = Field(default="", max_length=4000)


class InsuranceClaimUpdate(CamelModel):
    status: InsuranceClaimStatus
    approved_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    paid_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    denial_reason: str = Field(default="", max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)


class InsuranceClaimResponse(CamelModel):
    id: str
    patient_id: str
    branch_id: str | None = None
    charge_entry_id: str | None = None
    supporting_record_id: str | None = None
    payer_name: str
    claim_number: str
    status: str
    billed_amount: float
    approved_amount: float | None = None
    paid_amount: float
    currency: str
    submitted_at: datetime | None = None
    resolved_at: datetime | None = None
    denial_reason: str
    notes: str
    actor_id: str
    created_at: datetime
    updated_at: datetime


class PmsReconciliationRunResponse(CamelModel):
    id: str
    filename: str
    total_rows: int
    matched_rows: int
    mismatch_rows: int
    missing_local_rows: int
    missing_pms_rows: int
    duplicate_source_rows: int
    invalid_rows: int
    created_at: datetime


class PmsReconciliationRowResponse(CamelModel):
    id: str
    row_number: int | None = None
    status: str
    transaction_reference: str
    patient_reference: str
    local_ledger_entry_id: str | None = None
    entry_type: str | None = None
    external_amount: Decimal | None = None
    local_amount: Decimal | None = None
    currency: str
    details: str


class RecallAutomationSettingsUpdate(CamelModel):
    post_procedure_days: int = Field(ge=1, le=3650)
    pending_treatment_days: int = Field(ge=1, le=3650)
    hygiene_recall_days: int = Field(ge=1, le=3650)


class RecallReminderApproval(CamelModel):
    consent_confirmed: bool


class RecallAutomationSettingsResponse(CamelModel):
    post_procedure_days: int
    pending_treatment_days: int
    hygiene_recall_days: int
    updated_at: datetime


class LocalListingAuditUpsert(CamelModel):
    branch_id: str
    platform: str = Field(min_length=2, max_length=100)
    profile_url: str = Field(default="", max_length=500)
    primary_category: str = Field(default="", max_length=120)
    name_matches: bool = False
    address_matches: bool = False
    phone_matches: bool = False
    notes: str = Field(default="", max_length=2000)


class LocalListingAuditResponse(CamelModel):
    id: str
    branch_id: str
    platform: str
    profile_url: str
    primary_category: str
    name_matches: bool
    address_matches: bool
    phone_matches: bool
    notes: str
    last_reviewed_at: datetime


class MarketingCampaignCreate(CamelModel):
    branch_id: str | None = None
    title: str = Field(min_length=2, max_length=160)
    channel: Literal["social", "email", "local", "community", "other"]
    objective: str = Field(default="", max_length=1000)
    status: Literal["draft", "planned"] = "draft"
    start_at: datetime | None = None
    end_at: datetime | None = None
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.start_at and self.start_at.tzinfo is None:
            raise ValueError("Campaign start time must include a timezone.")
        if self.end_at and self.end_at.tzinfo is None:
            raise ValueError("Campaign end time must include a timezone.")
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValueError("Campaign end time must be after its start time.")
        return self


class MarketingCampaignUpdate(CamelModel):
    status: Literal["draft", "planned", "active", "paused", "completed"]


class MarketingCampaignResponse(CamelModel):
    id: str
    branch_id: str | None = None
    title: str
    channel: str
    objective: str
    status: str
    start_at: datetime | None = None
    end_at: datetime | None = None
    notes: str
    created_at: datetime
    updated_at: datetime


class ClinicReviewCreate(CamelModel):
    branch_id: str | None = None
    platform: str = Field(min_length=2, max_length=100)
    reviewer_name: str = Field(default="", max_length=120)
    rating: int = Field(ge=1, le=5)
    review_text: str = Field(min_length=1, max_length=5000)
    review_date: datetime | None = None


class ClinicReviewDraftUpdate(CamelModel):
    response_draft: str | None = Field(default=None, max_length=2000)


class ClinicReviewResponse(CamelModel):
    id: str
    branch_id: str | None = None
    platform: str
    reviewer_name: str
    rating: int
    review_text: str
    response_draft: str | None = None
    response_status: str
    review_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TreatmentStageCreate(CamelModel):
    name: str
    description: str = ""
    status: Literal["recommended", "accepted", "deferred", "declined", "scheduled", "completed"] = "recommended"
    estimated_value: float = 0
    reason: str | None = None
    scheduled_at: datetime | None = None


class TreatmentStageUpdate(CamelModel):
    status: Literal["recommended", "accepted", "deferred", "declined", "scheduled", "completed"]
    reason: str | None = None
    scheduled_at: datetime | None = None


class TreatmentStageResponse(CamelModel):
    id: str
    name: str
    description: str
    status: str
    estimated_value: float
    reason: str | None = None
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
    updated_by: str
    created_at: datetime


class TreatmentDecisionResponse(CamelModel):
    id: str
    patient_id: str
    stage_id: str
    decision: str
    reason: str | None = None
    actor_id: str
    actor_role: str
    created_at: datetime


class TreatmentPlanCreate(CamelModel):
    patient_id: str
    title: str
    notes: str = ""
    clinician_name: str
    estimated_value: float = 0
    currency: str = "INR"
    stages: list[TreatmentStageCreate] = []


class TreatmentPlanResponse(CamelModel):
    id: str
    patient_id: str
    title: str
    notes: str
    clinician_name: str
    status: str
    estimated_value: float
    currency: str
    stages: list[TreatmentStageResponse] = []
    created_at: datetime
    updated_at: datetime


class HealthRecordCreate(CamelModel):
    patient_id: str
    record_type: Literal["xray", "estimate", "prescription", "visit-summary", "lab-report", "image", "document"]
    title: str
    source_name: str
    author_name: str | None = None
    document_url: str | None = None
    metadata_json: dict = {}


class HealthRecordResponse(CamelModel):
    id: str
    patient_id: str
    record_type: str
    title: str
    source_name: str
    author_name: str | None = None
    document_url: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    file_sha256: str | None = None
    metadata_json: dict
    provenance_hash: str
    version_number: int = 1
    created_at: datetime


class HealthRecordCorrection(CamelModel):
    title: str | None = None
    source_name: str | None = None
    author_name: str | None = None
    document_url: str | None = None
    metadata_json: dict | None = None
    correction_reason: str = Field(min_length=5, max_length=1000)


class HealthRecordRevisionResponse(CamelModel):
    id: str
    record_id: str
    revision_number: int
    snapshot: dict
    correction_reason: str
    actor_id: str
    created_at: datetime


class RecordConsentCreate(CamelModel):
    patient_id: str
    purpose: str
    recipient_name: str
    record_ids: list[str] = Field(min_length=1, max_length=100)
    scope: list[Literal["view", "download", "share"]] = ["view"]
    expires_at: datetime | None = None


class RecordConsentResponse(CamelModel):
    id: str
    patient_id: str
    purpose: str
    recipient_name: str
    record_ids: list[str]
    scope: list[str] = ["view"]
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class RecallReminderCreate(CamelModel):
    patient_id: str
    reminder_type: Literal["review", "hygiene", "post-procedure", "pending-visit"]
    message: str
    channel: Literal["email", "sms", "whatsapp", "phone"] = "email"
    scheduled_at: datetime
    consent_confirmed: bool


class RecallReminderUpdate(CamelModel):
    status: Literal["sent", "completed", "failed", "cancelled"]


class RecallReminderResponse(CamelModel):
    id: str
    patient_id: str
    reminder_type: str
    message: str
    channel: str
    scheduled_at: datetime
    status: str
    consent_confirmed: bool
    consent_confirmed_by: str | None = None
    consent_confirmed_at: datetime | None = None
    created_at: datetime


class RevenueRecoverySummary(CamelModel):
    deferred_value: float
    declined_value: float
    accepted_value: float
    completed_value: float
    pending_stage_count: int
    overdue_stage_count: int
    pending_value: float = 0
    overdue_value: float = 0
    decision_count: int = 0
    conversion_rate: float = 0
    completion_rate: float = 0
    currency: str
    charges_value: float = 0
    payments_received: float = 0
    refunds_value: float = 0
    net_collected: float = 0
    outstanding_balance: float = 0
    ledger_entry_count: int = 0


class ClinicPerformanceAnalytics(CamelModel):
    total_treatment_stages: int
    accepted_stages: int
    completed_stages: int
    open_followups: int
    overdue_followups: int
    completed_followups: int
    workflow_completion_rate: float
    followup_completion_rate: float
    decision_count: int
    branch_count: int
    completed_visits: int = 0
    unique_patients_seen: int = 0
    returning_patients: int = 0
    patient_retention_rate: float = 0
    no_show_visits: int = 0
    scheduled_visits: int = 0
    open_enquiries: int = 0
    pending_reminder_approvals: int = 0
    from_date: datetime | None = None
    to_date: datetime | None = None


class PortalShareCreate(CamelModel):
    purpose: str = Field(min_length=3, max_length=200)
    recipient_name: str = Field(min_length=2, max_length=120)
    record_ids: list[str] = Field(min_length=1, max_length=100)
    scope: list[Literal["view", "download"]] = ["view"]
    expires_at: datetime


class PortalShareResponse(CamelModel):
    consent_id: str
    share_token: str
    expires_at: datetime


class PortalShareView(CamelModel):
    purpose: str
    recipient_name: str
    records: list[HealthRecordResponse]
    expires_at: datetime


class PortalInvitationCreate(CamelModel):
    patient_id: str


class PortalInvitationResponse(CamelModel):
    invitation_token: str
    expires_at: datetime
    clinic_id: str
    email: EmailStr


class PortalInvitationAccept(CamelModel):
    invitation_token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=128)


class PortalLogin(CamelModel):
    clinic_id: str
    email: EmailStr
    password: str


class PortalLoginResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"
    patient: PatientResponse


class IntegrationSyncResponse(CamelModel):
    id: str
    connection_id: str | None = None
    job_type: str
    status: str
    field_mapping: dict
    processed_count: int
    failed_count: int
    errors: list[dict]
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class AuditEventResponse(CamelModel):
    id: str
    actor_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    detail: dict
    created_at: datetime


class IntegrationConnectionCreate(CamelModel):
    provider: str = Field(min_length=2, max_length=120)
    integration_type: Literal[
        "pms",
        "accounting",
        "insurance",
        "imaging",
        "digital-dentistry",
        "equipment",
        "robotics",
        "payments",
        "communications",
        "marketing",
    ]
    configuration_json: dict = Field(default_factory=dict)


class IntegrationConnectionResponse(CamelModel):
    id: str
    provider: str
    integration_type: str
    status: str
    configuration_json: dict
    last_synced_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime


class CommunicationTemplateCreate(CamelModel):
    name: str = Field(min_length=2, max_length=160)
    channel: Literal["email", "sms", "whatsapp", "push"]
    subject: str | None = Field(default=None, max_length=200)
    body_template: str = Field(min_length=1, max_length=10000)
    variables: list[str] = []


class CommunicationTemplateUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    channel: Literal["email", "sms", "whatsapp", "push"] | None = None
    subject: str | None = Field(default=None, max_length=200)
    body_template: str | None = Field(default=None, min_length=1, max_length=10000)
    variables: list[str] | None = None
    is_active: bool | None = None


class CommunicationTemplateResponse(CamelModel):
    id: str
    clinic_id: str
    name: str
    channel: str
    subject: str | None = None
    body_template: str
    variables: list[str] = []
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


class CommunicationOutboxCreate(CamelModel):
    patient_id: str
    channel: Literal["email", "sms", "whatsapp", "push"]
    recipient: str
    subject: str | None = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    template_id: str | None = None


class CommunicationOutboxResponse(CamelModel):
    id: str
    clinic_id: str
    patient_id: str
    channel: str
    recipient: str
    subject: str | None = None
    status: str
    attempt_count: int
    max_attempts: int
    available_at: datetime
    sent_at: datetime | None = None
    last_error: str | None = None
    external_id: str | None = None
    created_by: str
    created_at: datetime
