from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DentalWorkflowCase(Base):
    __tablename__ = "dental_workflow_cases"
    __table_args__ = (
        Index("ix_dental_workflow_cases_clinic_type_status", "clinic_id", "case_type", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    clinic_id: Mapped[str] = mapped_column(String, ForeignKey("clinics.id"), nullable=False, index=True)
    branch_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("clinic_branches.id"), nullable=True, index=True
    )
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"), nullable=False, index=True)
    treatment_stage_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("treatment_stages.id"), nullable=True
    )
    case_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="requested", index=True)
    provider_name: Mapped[str] = mapped_column(String, default="")
    external_reference: Mapped[str] = mapped_column(String, default="")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class DentalWorkflowEvent(Base):
    __tablename__ = "dental_workflow_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    clinic_id: Mapped[str] = mapped_column(String, ForeignKey("clinics.id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(
        String, ForeignKey("dental_workflow_cases.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    actor_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ClinicAsset(Base):
    __tablename__ = "clinic_assets"
    __table_args__ = (
        UniqueConstraint("clinic_id", "asset_tag", name="uq_clinic_asset_tag"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    clinic_id: Mapped[str] = mapped_column(String, ForeignKey("clinics.id"), nullable=False, index=True)
    branch_id: Mapped[str] = mapped_column(
        String, ForeignKey("clinic_branches.id"), nullable=False, index=True
    )
    asset_tag: Mapped[str] = mapped_column(String, nullable=False)
    asset_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, default="")
    serial_number: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="active", index=True)
    next_service_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class AssetMaintenanceRecord(Base):
    __tablename__ = "asset_maintenance_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    clinic_id: Mapped[str] = mapped_column(String, ForeignKey("clinics.id"), nullable=False, index=True)
    branch_id: Mapped[str] = mapped_column(
        String, ForeignKey("clinic_branches.id"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(String, ForeignKey("clinic_assets.id"), nullable=False, index=True)
    work_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="planned", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SterilizationCycle(Base):
    __tablename__ = "sterilization_cycles"
    __table_args__ = (
        UniqueConstraint("clinic_id", "cycle_reference", name="uq_sterilization_cycle_reference"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    clinic_id: Mapped[str] = mapped_column(String, ForeignKey("clinics.id"), nullable=False, index=True)
    branch_id: Mapped[str] = mapped_column(
        String, ForeignKey("clinic_branches.id"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(String, ForeignKey("clinic_assets.id"), nullable=False, index=True)
    cycle_reference: Mapped[str] = mapped_column(String, nullable=False)
    load_reference: Mapped[str] = mapped_column(String, default="")
    result: Mapped[str] = mapped_column(String, nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operator_name: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class PatientMessageDraft(Base):
    __tablename__ = "patient_message_drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    clinic_id: Mapped[str] = mapped_column(String, ForeignKey("clinics.id"), nullable=False, index=True)
    branch_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("clinic_branches.id"), nullable=True, index=True
    )
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft", index=True)
    consent_confirmed: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class MarketingPublicationDraft(Base):
    __tablename__ = "marketing_publication_drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    clinic_id: Mapped[str] = mapped_column(String, ForeignKey("clinics.id"), nullable=False, index=True)
    branch_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("clinic_branches.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft", index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ClinicalNoteDraft(Base):
    __tablename__ = "clinical_note_drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    clinic_id: Mapped[str] = mapped_column(String, ForeignKey("clinics.id"), nullable=False, index=True)
    branch_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("clinic_branches.id"), nullable=True, index=True
    )
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"), nullable=False, index=True)
    visit_id: Mapped[str | None] = mapped_column(String, ForeignKey("patient_visits.id"), nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    clinician_input: Mapped[str] = mapped_column(Text, nullable=False)
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    generation_source: Mapped[str] = mapped_column(String, default="clinician", nullable=False)
    review_status: Mapped[str] = mapped_column(String, default="pending-review", index=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
