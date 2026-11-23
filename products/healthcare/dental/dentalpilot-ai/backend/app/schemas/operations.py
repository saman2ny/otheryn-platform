from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import CamelModel

DentalCaseType = Literal[
    "imaging", "intraoral-scan", "lab", "cad-cam", "3d-print", "implant", "robotics"
]
DentalCaseStatus = Literal[
    "requested", "planning", "in-progress", "awaiting-clinician", "completed", "cancelled"
]


class DentalWorkflowCaseCreate(CamelModel):
    branch_id: str | None = None
    patient_id: str
    treatment_stage_id: str | None = None
    case_type: DentalCaseType
    title: str = Field(min_length=2, max_length=200)
    provider_name: str = Field(default="", max_length=160)
    external_reference: str = Field(default="", max_length=160)
    due_at: datetime | None = None
    details: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_due_at(self):
        if self.due_at is not None and self.due_at.tzinfo is None:
            raise ValueError("Case due time must include a timezone.")
        return self


class DentalWorkflowCaseUpdate(CamelModel):
    status: DentalCaseStatus


class DentalWorkflowCaseResponse(CamelModel):
    id: str
    branch_id: str | None = None
    patient_id: str
    treatment_stage_id: str | None = None
    case_type: str
    title: str
    status: str
    provider_name: str
    external_reference: str
    due_at: datetime | None = None
    details: dict
    created_by: str
    created_at: datetime
    updated_at: datetime


class DentalWorkflowEventCreate(CamelModel):
    event_type: Literal["milestone", "handoff", "approval", "note"]
    title: str = Field(min_length=2, max_length=160)
    notes: str = Field(default="", max_length=2000)


class DentalWorkflowEventResponse(CamelModel):
    id: str
    case_id: str
    event_type: str
    title: str
    notes: str
    actor_id: str
    created_at: datetime


AssetType = Literal[
    "dental-chair", "autoclave", "intraoral-scanner", "xray", "cbct", "3d-printer", "surgical-robot", "other"
]


class ClinicAssetCreate(CamelModel):
    branch_id: str
    asset_tag: str = Field(min_length=2, max_length=80)
    asset_type: AssetType
    display_name: str = Field(min_length=2, max_length=160)
    model_name: str = Field(default="", max_length=160)
    serial_number: str = Field(default="", max_length=160)
    next_service_at: datetime | None = None
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_service_time(self):
        if self.next_service_at is not None and self.next_service_at.tzinfo is None:
            raise ValueError("Next service time must include a timezone.")
        return self


class ClinicAssetUpdate(CamelModel):
    status: Literal["active", "service-due", "unavailable", "retired"]
    next_service_at: datetime | None = None
    notes: str = Field(default="", max_length=2000)


class ClinicAssetResponse(CamelModel):
    id: str
    branch_id: str
    asset_tag: str
    asset_type: str
    display_name: str
    model_name: str
    serial_number: str
    status: str
    next_service_at: datetime | None = None
    notes: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class AssetMaintenanceCreate(CamelModel):
    work_type: Literal["maintenance", "breakdown", "repair", "calibration"]
    due_at: datetime | None = None
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_due_time(self):
        if self.due_at is not None and self.due_at.tzinfo is None:
            raise ValueError("Maintenance due time must include a timezone.")
        return self


class AssetMaintenanceUpdate(CamelModel):
    status: Literal["planned", "in-progress", "completed", "cancelled"]
    notes: str = Field(default="", max_length=2000)


class AssetMaintenanceResponse(CamelModel):
    id: str
    asset_id: str
    work_type: str
    status: str
    due_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str
    created_by: str
    created_at: datetime


class SterilizationCycleCreate(CamelModel):
    branch_id: str
    asset_id: str
    cycle_reference: str = Field(min_length=2, max_length=120)
    load_reference: str = Field(default="", max_length=120)
    result: Literal["passed", "failed", "needs-review"]
    started_at: datetime
    completed_at: datetime | None = None
    operator_name: str = Field(min_length=2, max_length=120)
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_cycle_times(self):
        if self.started_at.tzinfo is None or (
            self.completed_at is not None and self.completed_at.tzinfo is None
        ):
            raise ValueError("Sterilization timestamps must include a timezone.")
        if self.completed_at and self.completed_at < self.started_at:
            raise ValueError("Cycle completion cannot precede its start.")
        return self


class SterilizationCycleResponse(CamelModel):
    id: str
    branch_id: str
    asset_id: str
    cycle_reference: str
    load_reference: str
    result: str
    started_at: datetime
    completed_at: datetime | None = None
    operator_name: str
    notes: str
    recorded_by: str
    created_at: datetime


class PatientMessageDraftCreate(CamelModel):
    patient_id: str
    branch_id: str | None = None
    channel: Literal["email", "sms", "whatsapp"]
    subject: str = Field(default="", max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    consent_confirmed: bool


class PatientMessageDraftUpdate(CamelModel):
    status: Literal["approved", "cancelled"]


class PatientMessageDraftResponse(CamelModel):
    id: str
    patient_id: str
    branch_id: str | None = None
    channel: str
    subject: str
    body: str
    status: str
    consent_confirmed: bool
    created_by: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime


class MarketingPublicationDraftCreate(CamelModel):
    branch_id: str | None = None
    title: str = Field(min_length=2, max_length=160)
    platform: Literal["google-business", "meta", "other"]
    body: str = Field(min_length=1, max_length=5000)
    scheduled_at: datetime | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.scheduled_at is not None and self.scheduled_at.tzinfo is None:
            raise ValueError("Publication schedule must include a timezone.")
        return self


class MarketingPublicationDraftUpdate(CamelModel):
    status: Literal["approved", "scheduled", "published", "cancelled"]
    scheduled_at: datetime | None = None


class MarketingPublicationDraftResponse(CamelModel):
    id: str
    branch_id: str | None = None
    title: str
    platform: str
    body: str
    status: str
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    created_by: str
    reviewed_by: str | None = None
    created_at: datetime


class ClinicalNoteDraftCreate(CamelModel):
    patient_id: str
    visit_id: str | None = None
    title: str = Field(min_length=2, max_length=160)
    clinician_input: str = Field(min_length=10, max_length=8000)


class ClinicalNoteDraftReview(CamelModel):
    review_status: Literal["approved", "rejected"]


class ClinicalNoteDraftResponse(CamelModel):
    id: str
    patient_id: str
    visit_id: str | None = None
    title: str
    clinician_input: str
    draft_text: str
    generation_source: str
    review_status: str
    created_by: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class ClinicalNoteAiGenerationRequest(CamelModel):
    patient_consent_confirmed: bool
