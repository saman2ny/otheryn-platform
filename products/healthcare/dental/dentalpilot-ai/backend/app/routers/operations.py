import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.models.healthcare import (
    AuditEvent,
    ClinicBranch,
    Patient,
    PatientVisit,
    TreatmentPlan,
    TreatmentStage,
)
from app.models.operations import (
    AssetMaintenanceRecord,
    ClinicAsset,
    ClinicalNoteDraft,
    DentalWorkflowCase,
    DentalWorkflowEvent,
    MarketingPublicationDraft,
    PatientMessageDraft,
    SterilizationCycle,
)
from app.schemas.operations import (
    AssetMaintenanceCreate,
    AssetMaintenanceResponse,
    AssetMaintenanceUpdate,
    ClinicAssetCreate,
    ClinicAssetResponse,
    ClinicAssetUpdate,
    ClinicalNoteAiGenerationRequest,
    ClinicalNoteDraftCreate,
    ClinicalNoteDraftResponse,
    ClinicalNoteDraftReview,
    DentalWorkflowCaseCreate,
    DentalWorkflowCaseResponse,
    DentalWorkflowCaseUpdate,
    DentalWorkflowEventCreate,
    DentalWorkflowEventResponse,
    MarketingPublicationDraftCreate,
    MarketingPublicationDraftResponse,
    MarketingPublicationDraftUpdate,
    PatientMessageDraftCreate,
    PatientMessageDraftResponse,
    PatientMessageDraftUpdate,
    SterilizationCycleCreate,
    SterilizationCycleResponse,
)
from app.services.clinical_notes import ClinicalNoteGenerationError, generate_clinical_note

router = APIRouter(prefix="/operations", tags=["dental-operations"])

CASE_TRANSITIONS = {
    "requested": {"planning", "cancelled"},
    "planning": {"in-progress", "cancelled"},
    "in-progress": {"awaiting-clinician", "cancelled"},
    "awaiting-clinician": {"in-progress", "completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}
MAINTENANCE_TRANSITIONS = {
    "planned": {"in-progress", "cancelled"},
    "in-progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}
PUBLICATION_TRANSITIONS = {
    "draft": {"approved", "cancelled"},
    "approved": {"scheduled", "published", "cancelled"},
    "scheduled": {"published", "cancelled"},
    "published": set(),
    "cancelled": set(),
}


def _require_clinic_staff(current_user: CurrentUser) -> None:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")


def _branch_for_user(
    db: DbSession,
    current_user: CurrentUser,
    branch_id: str | None,
    *,
    required: bool = False,
) -> str | None:
    selected_branch_id = branch_id or current_user.branch_id
    if selected_branch_id is None:
        if required:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "A clinic branch is required.")
        return None
    branch = (
        db.query(ClinicBranch)
        .filter(
            ClinicBranch.id == selected_branch_id,
            ClinicBranch.clinic_id == current_user.clinic_id,
        )
        .first()
    )
    if branch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinic branch not found.")
    if current_user.role == "staff" and current_user.branch_id != branch.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic branch access denied.")
    return branch.id


def _patient_for_user(db: DbSession, current_user: CurrentUser, patient_id: str) -> Patient:
    query = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.clinic_id == current_user.clinic_id,
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    patient = query.first()
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    return patient


def _audit(
    db: DbSession,
    current_user: CurrentUser,
    action: str,
    resource_type: str,
    resource_id: str,
    branch_id: str | None = None,
) -> None:
    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            branch_id=branch_id or current_user.branch_id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    )


def _case_query(db: DbSession, current_user: CurrentUser):
    query = db.query(DentalWorkflowCase).filter(
        DentalWorkflowCase.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(DentalWorkflowCase.branch_id == current_user.branch_id)
    return query


@router.get("/dental-cases", response_model=list[DentalWorkflowCaseResponse])
def list_dental_cases(current_user: CurrentUser, db: DbSession) -> list[DentalWorkflowCase]:
    _require_clinic_staff(current_user)
    return _case_query(db, current_user).order_by(DentalWorkflowCase.updated_at.desc()).limit(500).all()


@router.post(
    "/dental-cases",
    response_model=DentalWorkflowCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dental_case(
    request: DentalWorkflowCaseCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> DentalWorkflowCase:
    _require_clinic_staff(current_user)
    patient = _patient_for_user(db, current_user, request.patient_id)
    branch_id = _branch_for_user(
        db, current_user, request.branch_id or patient.branch_id
    )
    if patient.branch_id and branch_id != patient.branch_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The case branch must match the patient's assigned branch.",
        )
    if request.treatment_stage_id:
        stage = (
            db.query(TreatmentStage)
            .join(TreatmentPlan, TreatmentPlan.id == TreatmentStage.plan_id)
            .filter(
                TreatmentStage.id == request.treatment_stage_id,
                TreatmentStage.clinic_id == current_user.clinic_id,
                TreatmentPlan.patient_id == patient.id,
            )
            .first()
        )
        if stage is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Treatment stage not found.")
    case = DentalWorkflowCase(
        clinic_id=current_user.clinic_id,
        branch_id=branch_id,
        patient_id=patient.id,
        status="requested",
        created_by=current_user.id,
        **request.model_dump(exclude={"branch_id", "patient_id"}),
    )
    db.add(case)
    db.flush()
    db.add(
        DentalWorkflowEvent(
            clinic_id=current_user.clinic_id,
            case_id=case.id,
            event_type="milestone",
            title="Case created",
            actor_id=current_user.id,
        )
    )
    _audit(db, current_user, "create", "dental-workflow-case", case.id, branch_id)
    db.commit()
    db.refresh(case)
    return case


@router.patch("/dental-cases/{case_id}", response_model=DentalWorkflowCaseResponse)
def update_dental_case(
    case_id: str,
    request: DentalWorkflowCaseUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> DentalWorkflowCase:
    _require_clinic_staff(current_user)
    case = _case_query(db, current_user).filter(DentalWorkflowCase.id == case_id).first()
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dental workflow case not found.")
    if request.status != case.status and request.status not in CASE_TRANSITIONS[case.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot change case status from {case.status} to {request.status}.",
        )
    case.status = request.status
    db.add(
        DentalWorkflowEvent(
            clinic_id=current_user.clinic_id,
            case_id=case.id,
            event_type="milestone",
            title=f"Case status changed to {case.status}",
            actor_id=current_user.id,
        )
    )
    _audit(db, current_user, "update", "dental-workflow-case", case.id, case.branch_id)
    db.commit()
    db.refresh(case)
    return case


@router.get(
    "/dental-cases/{case_id}/events",
    response_model=list[DentalWorkflowEventResponse],
)
def list_dental_case_events(
    case_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> list[DentalWorkflowEvent]:
    _require_clinic_staff(current_user)
    case = _case_query(db, current_user).filter(DentalWorkflowCase.id == case_id).first()
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dental workflow case not found.")
    return (
        db.query(DentalWorkflowEvent)
        .filter(
            DentalWorkflowEvent.clinic_id == current_user.clinic_id,
            DentalWorkflowEvent.case_id == case.id,
        )
        .order_by(DentalWorkflowEvent.created_at.asc())
        .all()
    )


@router.post(
    "/dental-cases/{case_id}/events",
    response_model=DentalWorkflowEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dental_case_event(
    case_id: str,
    request: DentalWorkflowEventCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> DentalWorkflowEvent:
    _require_clinic_staff(current_user)
    case = _case_query(db, current_user).filter(DentalWorkflowCase.id == case_id).first()
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dental workflow case not found.")
    event = DentalWorkflowEvent(
        clinic_id=current_user.clinic_id,
        case_id=case.id,
        actor_id=current_user.id,
        **request.model_dump(),
    )
    db.add(event)
    _audit(db, current_user, "create", "dental-workflow-event", event.id, case.branch_id)
    db.commit()
    db.refresh(event)
    return event


def _asset_query(db: DbSession, current_user: CurrentUser):
    query = db.query(ClinicAsset).filter(ClinicAsset.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(ClinicAsset.branch_id == current_user.branch_id)
    return query


@router.get("/assets", response_model=list[ClinicAssetResponse])
def list_clinic_assets(current_user: CurrentUser, db: DbSession) -> list[ClinicAsset]:
    _require_clinic_staff(current_user)
    return _asset_query(db, current_user).order_by(ClinicAsset.display_name.asc()).all()


@router.post("/assets", response_model=ClinicAssetResponse, status_code=status.HTTP_201_CREATED)
def create_clinic_asset(
    request: ClinicAssetCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ClinicAsset:
    _require_clinic_staff(current_user)
    branch_id = _branch_for_user(db, current_user, request.branch_id, required=True)
    asset = ClinicAsset(
        clinic_id=current_user.clinic_id,
        branch_id=branch_id,
        created_by=current_user.id,
        **request.model_dump(exclude={"branch_id"}),
    )
    db.add(asset)
    try:
        db.flush()
        _audit(db, current_user, "create", "clinic-asset", asset.id, branch_id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Asset tag already exists in this clinic.") from exc
    db.refresh(asset)
    return asset


@router.patch("/assets/{asset_id}", response_model=ClinicAssetResponse)
def update_clinic_asset(
    asset_id: str,
    request: ClinicAssetUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ClinicAsset:
    _require_clinic_staff(current_user)
    asset = _asset_query(db, current_user).filter(ClinicAsset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinic asset not found.")
    if (
        request.next_service_at is not None
        and request.next_service_at.tzinfo is None
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Next service time must include a timezone.")
    changes = request.model_dump(exclude_unset=True)
    if "status" in changes:
        asset.status = request.status
    if "next_service_at" in changes:
        asset.next_service_at = request.next_service_at
    if "notes" in changes:
        asset.notes = request.notes.strip()
    _audit(db, current_user, "update", "clinic-asset", asset.id, asset.branch_id)
    db.commit()
    db.refresh(asset)
    return asset


@router.get(
    "/assets/{asset_id}/maintenance",
    response_model=list[AssetMaintenanceResponse],
)
def list_asset_maintenance(
    asset_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> list[AssetMaintenanceRecord]:
    _require_clinic_staff(current_user)
    asset = _asset_query(db, current_user).filter(ClinicAsset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinic asset not found.")
    return (
        db.query(AssetMaintenanceRecord)
        .filter(
            AssetMaintenanceRecord.clinic_id == current_user.clinic_id,
            AssetMaintenanceRecord.asset_id == asset.id,
        )
        .order_by(AssetMaintenanceRecord.created_at.desc())
        .all()
    )


@router.post(
    "/assets/{asset_id}/maintenance",
    response_model=AssetMaintenanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_maintenance(
    asset_id: str,
    request: AssetMaintenanceCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> AssetMaintenanceRecord:
    _require_clinic_staff(current_user)
    asset = _asset_query(db, current_user).filter(ClinicAsset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinic asset not found.")
    record = AssetMaintenanceRecord(
        clinic_id=current_user.clinic_id,
        branch_id=asset.branch_id,
        asset_id=asset.id,
        created_by=current_user.id,
        **request.model_dump(),
    )
    db.add(record)
    _audit(db, current_user, "create", "asset-maintenance", record.id, asset.branch_id)
    db.commit()
    db.refresh(record)
    return record


@router.patch(
    "/assets/{asset_id}/maintenance/{record_id}",
    response_model=AssetMaintenanceResponse,
)
def update_asset_maintenance(
    asset_id: str,
    record_id: str,
    request: AssetMaintenanceUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> AssetMaintenanceRecord:
    _require_clinic_staff(current_user)
    asset = _asset_query(db, current_user).filter(ClinicAsset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinic asset not found.")
    record = (
        db.query(AssetMaintenanceRecord)
        .filter(
            AssetMaintenanceRecord.id == record_id,
            AssetMaintenanceRecord.clinic_id == current_user.clinic_id,
            AssetMaintenanceRecord.asset_id == asset.id,
        )
        .first()
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Maintenance record not found.")
    if request.status != record.status and request.status not in MAINTENANCE_TRANSITIONS[record.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot change maintenance status from {record.status} to {request.status}.",
        )
    record.status = request.status
    record.notes = request.notes.strip()
    if request.status == "completed":
        record.completed_at = datetime.now(timezone.utc)
    _audit(db, current_user, "update", "asset-maintenance", record.id, asset.branch_id)
    db.commit()
    db.refresh(record)
    return record


@router.get("/sterilization-cycles", response_model=list[SterilizationCycleResponse])
def list_sterilization_cycles(
    current_user: CurrentUser,
    db: DbSession,
) -> list[SterilizationCycle]:
    _require_clinic_staff(current_user)
    query = db.query(SterilizationCycle).filter(
        SterilizationCycle.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(SterilizationCycle.branch_id == current_user.branch_id)
    return query.order_by(SterilizationCycle.started_at.desc()).limit(500).all()


@router.post(
    "/sterilization-cycles",
    response_model=SterilizationCycleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_sterilization_cycle(
    request: SterilizationCycleCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> SterilizationCycle:
    _require_clinic_staff(current_user)
    branch_id = _branch_for_user(db, current_user, request.branch_id, required=True)
    asset = _asset_query(db, current_user).filter(ClinicAsset.id == request.asset_id).first()
    if asset is None or asset.branch_id != branch_id or asset.asset_type != "autoclave":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Select an autoclave asset assigned to this clinic branch.",
        )
    cycle = SterilizationCycle(
        clinic_id=current_user.clinic_id,
        branch_id=branch_id,
        recorded_by=current_user.id,
        **request.model_dump(exclude={"branch_id"}),
    )
    db.add(cycle)
    if request.result == "failed":
        asset.status = "unavailable"
    try:
        db.flush()
        _audit(db, current_user, "create", "sterilization-cycle", cycle.id, branch_id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Cycle reference already exists in this clinic.") from exc
    db.refresh(cycle)
    return cycle


@router.get("/message-drafts", response_model=list[PatientMessageDraftResponse])
def list_patient_message_drafts(
    current_user: CurrentUser,
    db: DbSession,
) -> list[PatientMessageDraft]:
    _require_clinic_staff(current_user)
    query = db.query(PatientMessageDraft).filter(
        PatientMessageDraft.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(PatientMessageDraft.branch_id == current_user.branch_id)
    return query.order_by(PatientMessageDraft.created_at.desc()).limit(500).all()


@router.post(
    "/message-drafts",
    response_model=PatientMessageDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient_message_draft(
    request: PatientMessageDraftCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientMessageDraft:
    _require_clinic_staff(current_user)
    patient = _patient_for_user(db, current_user, request.patient_id)
    branch_id = _branch_for_user(db, current_user, request.branch_id or patient.branch_id)
    if patient.branch_id and branch_id != patient.branch_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Message branch must match the patient's branch.")
    if not request.consent_confirmed or patient.consent_channel != request.channel:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Confirm current consent for the selected patient communication channel.",
        )
    if request.channel == "email" and not patient.email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The patient has no email address on file.")
    if request.channel in ("sms", "whatsapp") and not patient.phone:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The patient has no phone number on file.")
    draft = PatientMessageDraft(
        clinic_id=current_user.clinic_id,
        patient_id=patient.id,
        branch_id=branch_id,
        channel=request.channel,
        subject=request.subject.strip(),
        body=request.body.strip(),
        consent_confirmed=True,
        created_by=current_user.id,
    )
    db.add(draft)
    db.flush()
    _audit(db, current_user, "create", "patient-message-draft", draft.id, branch_id)
    db.commit()
    db.refresh(draft)
    return draft


@router.patch("/message-drafts/{draft_id}", response_model=PatientMessageDraftResponse)
def update_patient_message_draft(
    draft_id: str,
    request: PatientMessageDraftUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientMessageDraft:
    _require_clinic_staff(current_user)
    query = db.query(PatientMessageDraft).filter(
        PatientMessageDraft.id == draft_id,
        PatientMessageDraft.clinic_id == current_user.clinic_id,
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(PatientMessageDraft.branch_id == current_user.branch_id)
    draft = query.first()
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient message draft not found.")
    if draft.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only draft messages can be approved or cancelled.")
    draft.status = request.status
    if request.status == "approved":
        if not draft.consent_confirmed:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Patient consent must be confirmed.")
        draft.approved_by = current_user.id
        draft.approved_at = datetime.now(timezone.utc)
    _audit(db, current_user, "update", "patient-message-draft", draft.id, draft.branch_id)
    db.commit()
    db.refresh(draft)
    return draft


@router.get(
    "/marketing-publications",
    response_model=list[MarketingPublicationDraftResponse],
)
def list_marketing_publications(
    current_user: CurrentUser,
    db: DbSession,
) -> list[MarketingPublicationDraft]:
    _require_clinic_staff(current_user)
    query = db.query(MarketingPublicationDraft).filter(
        MarketingPublicationDraft.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(
            (MarketingPublicationDraft.branch_id == current_user.branch_id)
            | (MarketingPublicationDraft.branch_id.is_(None))
        )
    return query.order_by(MarketingPublicationDraft.created_at.desc()).limit(500).all()


@router.post(
    "/marketing-publications",
    response_model=MarketingPublicationDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_marketing_publication(
    request: MarketingPublicationDraftCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> MarketingPublicationDraft:
    _require_clinic_staff(current_user)
    branch_id = _branch_for_user(db, current_user, request.branch_id)
    publication = MarketingPublicationDraft(
        clinic_id=current_user.clinic_id,
        branch_id=branch_id,
        created_by=current_user.id,
        **request.model_dump(exclude={"branch_id"}),
    )
    db.add(publication)
    db.flush()
    _audit(db, current_user, "create", "marketing-publication-draft", publication.id, branch_id)
    db.commit()
    db.refresh(publication)
    return publication


@router.patch(
    "/marketing-publications/{publication_id}",
    response_model=MarketingPublicationDraftResponse,
)
def update_marketing_publication(
    publication_id: str,
    request: MarketingPublicationDraftUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> MarketingPublicationDraft:
    _require_clinic_staff(current_user)
    query = db.query(MarketingPublicationDraft).filter(
        MarketingPublicationDraft.id == publication_id,
        MarketingPublicationDraft.clinic_id == current_user.clinic_id,
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(
            (MarketingPublicationDraft.branch_id == current_user.branch_id)
            | (MarketingPublicationDraft.branch_id.is_(None))
        )
    publication = query.first()
    if publication is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publication draft not found.")
    if request.status != publication.status and request.status not in PUBLICATION_TRANSITIONS[publication.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot change publication status from {publication.status} to {request.status}.",
        )
    if request.status == "scheduled":
        if request.scheduled_at is None or request.scheduled_at.tzinfo is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Choose a scheduled publication time with a timezone.",
            )
        publication.scheduled_at = request.scheduled_at.astimezone(timezone.utc)
    if request.status == "published":
        publication.published_at = datetime.now(timezone.utc)
        publication.reviewed_by = current_user.id
    elif request.status == "approved":
        publication.reviewed_by = current_user.id
    publication.status = request.status
    _audit(
        db,
        current_user,
        "update",
        "marketing-publication-draft",
        publication.id,
        publication.branch_id,
    )
    db.commit()
    db.refresh(publication)
    return publication


@router.get("/clinical-note-drafts", response_model=list[ClinicalNoteDraftResponse])
def list_clinical_note_drafts(
    current_user: CurrentUser,
    db: DbSession,
) -> list[ClinicalNoteDraft]:
    _require_clinic_staff(current_user)
    query = db.query(ClinicalNoteDraft).filter(
        ClinicalNoteDraft.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(
            (ClinicalNoteDraft.branch_id == current_user.branch_id)
            | (ClinicalNoteDraft.branch_id.is_(None))
        )
    return query.order_by(ClinicalNoteDraft.created_at.desc()).limit(500).all()


@router.post(
    "/clinical-note-drafts",
    response_model=ClinicalNoteDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_clinical_note_draft(
    request: ClinicalNoteDraftCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ClinicalNoteDraft:
    _require_clinic_staff(current_user)
    patient = _patient_for_user(db, current_user, request.patient_id)
    branch_id = _branch_for_user(db, current_user, patient.branch_id)
    if request.visit_id:
        visit = (
            db.query(PatientVisit)
            .filter(
                PatientVisit.id == request.visit_id,
                PatientVisit.clinic_id == current_user.clinic_id,
                PatientVisit.patient_id == patient.id,
            )
            .first()
        )
        if visit is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient visit not found.")
    draft_text = request.clinician_input.strip()
    note = ClinicalNoteDraft(
        clinic_id=current_user.clinic_id,
        branch_id=branch_id,
        patient_id=patient.id,
        title=request.title.strip(),
        clinician_input=draft_text,
        draft_text=draft_text,
        created_by=current_user.id,
        visit_id=request.visit_id,
    )
    db.add(note)
    db.flush()
    _audit(db, current_user, "create", "clinical-note-draft", note.id, branch_id)
    db.commit()
    db.refresh(note)
    return note


@router.post(
    "/clinical-note-drafts/{draft_id}/generate-ai",
    response_model=ClinicalNoteDraftResponse,
)
def generate_clinical_note_draft(
    draft_id: str,
    request: ClinicalNoteAiGenerationRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ClinicalNoteDraft:
    _require_clinic_staff(current_user)
    if not request.patient_consent_confirmed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Confirm the patient's consent for AI-assisted note drafting.",
        )
    if not (
        settings.clinical_note_drafting_enabled
        and settings.clinical_ai_data_processing_approved
        and settings.anthropic_api_key
    ):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Clinical note drafting is not enabled for this deployment.",
        )
    if not current_user.clinic.clinical_note_drafting_enabled:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "A clinic owner must enable clinical note drafting first.",
        )
    query = db.query(ClinicalNoteDraft).filter(
        ClinicalNoteDraft.id == draft_id,
        ClinicalNoteDraft.clinic_id == current_user.clinic_id,
        ClinicalNoteDraft.review_status == "pending-review",
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(
            (ClinicalNoteDraft.branch_id == current_user.branch_id)
            | (ClinicalNoteDraft.branch_id.is_(None))
        )
    note = query.first()
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pending clinical note draft not found.")
    patient = _patient_for_user(db, current_user, note.patient_id)
    clinician_input = note.clinician_input
    for identifier in (patient.full_name, patient.email, patient.phone):
        if identifier and identifier.strip():
            clinician_input = re.sub(
                re.escape(identifier.strip()),
                "[PATIENT IDENTIFIER]",
                clinician_input,
                flags=re.IGNORECASE,
            )
    try:
        note.draft_text = generate_clinical_note(clinician_input)
    except ClinicalNoteGenerationError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "The clinical note draft could not be generated. The saved clinician input was not changed.",
        ) from exc
    note.generation_source = "anthropic"
    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            branch_id=note.branch_id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="generate",
            resource_type="clinical-note-ai-draft",
            resource_id=note.id,
            detail={
                "provider": "anthropic",
                "model": settings.anthropic_model,
                "patientConsentConfirmed": True,
            },
        )
    )
    db.commit()
    db.refresh(note)
    return note


@router.patch(
    "/clinical-note-drafts/{draft_id}/review",
    response_model=ClinicalNoteDraftResponse,
)
def review_clinical_note_draft(
    draft_id: str,
    request: ClinicalNoteDraftReview,
    current_user: CurrentUser,
    db: DbSession,
) -> ClinicalNoteDraft:
    _require_clinic_staff(current_user)
    query = db.query(ClinicalNoteDraft).filter(
        ClinicalNoteDraft.id == draft_id,
        ClinicalNoteDraft.clinic_id == current_user.clinic_id,
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(
            (ClinicalNoteDraft.branch_id == current_user.branch_id)
            | (ClinicalNoteDraft.branch_id.is_(None))
        )
    note = query.first()
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinical note draft not found.")
    if note.review_status != "pending-review":
        raise HTTPException(status.HTTP_409_CONFLICT, "This note draft has already been reviewed.")
    note.review_status = request.review_status
    note.reviewed_by = current_user.id
    note.reviewed_at = datetime.now(timezone.utc)
    _audit(db, current_user, "review", "clinical-note-draft", note.id, note.branch_id)
    db.commit()
    db.refresh(note)
    return note
