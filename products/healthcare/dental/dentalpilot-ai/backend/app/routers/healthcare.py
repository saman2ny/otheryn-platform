import csv
import io
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import PurePath
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.deps import CurrentUser, DbSession
from app.models.billing import PatientPaymentOrder
from app.core.config import settings
from app.models.healthcare import (
    AuditEvent,
    ClinicBranch,
    CommunicationOutbox,
    CommunicationTemplate,
    EmailOutbox,
    HealthRecord,
    HealthRecordRevision,
    IntegrationConnection,
    IntegrationSyncJob,
    InsuranceClaim,
    Patient,
    PatientCommunication,
    PatientEnquiry,
    PatientPortalAccount,
    PatientRecordShare,
    PatientVisit,
    PmsReconciliationRun,
    PmsReconciliationRow,
    RecallAutomationSettings,
    RecallReminder,
    RecordConsent,
    TreatmentLedgerEntry,
    TreatmentDecision,
    TreatmentPlan,
    TreatmentStage,
)
from app.schemas.healthcare import (
    AuditEventResponse,
    ClinicPerformanceAnalytics,
    CommunicationOutboxCreate,
    CommunicationOutboxResponse,
    CommunicationTemplateCreate,
    CommunicationTemplateResponse,
    CommunicationTemplateUpdate,
    EmailOutboxResponse,
    HealthRecordCorrection,
    HealthRecordCreate,
    HealthRecordResponse,
    HealthRecordRevisionResponse,
    InsuranceClaimCreate,
    InsuranceClaimResponse,
    InsuranceClaimUpdate,
    IntegrationSyncResponse,
    IntegrationConnectionCreate,
    IntegrationConnectionResponse,
    PatientCreate,
    PatientCommunicationCreate,
    PatientCommunicationResponse,
    PatientEmailCreate,
    PatientEnquiryCreate,
    PatientEnquiryResponse,
    PatientEnquiryUpdate,
    PatientResponse,
    PatientVisitCreate,
    PatientVisitResponse,
    PmsReconciliationRowResponse,
    PmsReconciliationRunResponse,
    RecallReminderCreate,
    RecallReminderApproval,
    RecallAutomationSettingsResponse,
    RecallAutomationSettingsUpdate,
    RecallReminderResponse,
    RecallReminderUpdate,
    RecordConsentCreate,
    RecordConsentResponse,
    RevenueRecoverySummary,
    TreatmentLedgerEntryCreate,
    TreatmentLedgerEntryResponse,
    TreatmentDecisionResponse,
    TreatmentPlanCreate,
    TreatmentPlanResponse,
    TreatmentStageResponse,
    TreatmentStageUpdate,
)
from app.services.document_storage import (
    DocumentStorageError,
    S3DocumentStorage,
    attachment_response,
)
from app.services.patient_payments import expire_stale_payment_orders

router = APIRouter(prefix="/healthcare", tags=["healthcare"])
logger = logging.getLogger(__name__)

SENSITIVE_CONFIG_KEYS = ("password", "secret", "token", "key", "credential", "private")
INSURANCE_CLAIM_TRANSITIONS = {
    "draft": {"submitted", "cancelled"},
    "submitted": {
        "in-review",
        "approved",
        "partially-approved",
        "denied",
        "cancelled",
    },
    "in-review": {"approved", "partially-approved", "denied", "cancelled"},
    "approved": {"partially-paid", "paid", "cancelled"},
    "partially-approved": {"partially-paid", "paid", "denied", "cancelled"},
    "partially-paid": {"partially-paid", "paid"},
    "paid": set(),
    "denied": set(),
    "cancelled": set(),
}
CSV_PATIENT_FIELDS = {
    "fullName",
    "email",
    "phone",
    "dateOfBirth",
    "externalReference",
}


def sanitized_integration_config(configuration: dict) -> dict:
    return {
        key: value
        for key, value in configuration.items()
        if not any(marker in key.lower() for marker in SENSITIVE_CONFIG_KEYS)
    }


def parse_patient_mapping(mapping_text: str, headers: list[str]) -> dict[str, str]:
    try:
        requested_mapping = json.loads(mapping_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Field mapping must be valid JSON.") from exc
    if not isinstance(requested_mapping, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Field mapping must be a JSON object.")
    mapping = requested_mapping or {
        field: field for field in CSV_PATIENT_FIELDS if field in headers
    }
    if any(field not in CSV_PATIENT_FIELDS for field in mapping):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Field mapping contains an unsupported patient field.")
    if any(not isinstance(header, str) or header not in headers for header in mapping.values()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Field mapping references a missing CSV column.")
    if "fullName" not in mapping:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Field mapping must include the patient's full name.")
    return mapping


def utc_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def audit(db: DbSession, current_user: CurrentUser, action: str, resource_type: str,
          resource_id: str | None = None, detail: dict | None = None) -> None:
    db.add(AuditEvent(
        clinic_id=current_user.clinic_id,
        branch_id=current_user.branch_id,
        actor_id=current_user.id,
        actor_type=current_user.role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail or {},
    ))


def primary_branch(db: DbSession, clinic_id: str) -> ClinicBranch:
    branch = (
        db.query(ClinicBranch)
        .filter(ClinicBranch.clinic_id == clinic_id, ClinicBranch.is_primary.is_(True))
        .first()
    )
    if branch is None:
        branch = ClinicBranch(clinic_id=clinic_id, name="Main branch", is_primary=True)
        db.add(branch)
        db.flush()
    return branch


def recall_settings(db: DbSession, clinic_id: str) -> RecallAutomationSettings:
    settings = db.query(RecallAutomationSettings).filter(
        RecallAutomationSettings.clinic_id == clinic_id
    ).first()
    if settings is None:
        settings = RecallAutomationSettings(
            clinic_id=clinic_id,
            post_procedure_days=1,
            pending_treatment_days=7,
            hygiene_recall_days=180,
        )
        db.add(settings)
        db.flush()
    return settings


def add_automatic_reminder(
    db: DbSession,
    current_user: CurrentUser,
    patient: Patient,
    reminder_type: str,
    delay_days: int,
    trigger_key: str,
    message: str,
) -> RecallReminder | None:
    if (
        db.query(RecallReminder.id)
        .filter(
            RecallReminder.clinic_id == current_user.clinic_id,
            RecallReminder.trigger_key == trigger_key,
        )
        .first()
    ):
        return None
    reminder = RecallReminder(
        clinic_id=current_user.clinic_id,
        patient_id=patient.id,
        reminder_type=reminder_type,
        message=message,
        channel="email" if patient.email else "phone",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=delay_days),
        status="pending-approval",
        consent_confirmed=False,
        trigger_key=trigger_key,
    )
    db.add(reminder)
    audit(
        db,
        current_user,
        "create",
        "automatic-recall-reminder",
        trigger_key,
        {"reminderType": reminder_type, "approvalRequired": True},
    )
    return reminder


def queue_patient_email(
    db: DbSession,
    current_user: CurrentUser,
    patient: Patient,
    subject: str,
    body_text: str,
    available_at: datetime,
    reminder_id: str | None = None,
) -> EmailOutbox:
    if not patient.email:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The patient does not have an email address on file.",
        )
    outbox = EmailOutbox(
        clinic_id=current_user.clinic_id,
        patient_id=patient.id,
        reminder_id=reminder_id,
        recipient_email=patient.email,
        subject=subject.strip(),
        body_text=body_text.strip(),
        available_at=utc_datetime(available_at),
        created_by=current_user.id,
    )
    db.add(outbox)
    db.flush()
    audit(
        db,
        current_user,
        "queue",
        "patient-email",
        outbox.id,
        {"scheduled": outbox.available_at > datetime.now(timezone.utc)},
    )
    return outbox


def clinic_patient(
    db: DbSession, current_user: CurrentUser, patient_id: str
) -> Patient | None:
    query = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.clinic_id == current_user.clinic_id,
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    return query.first()


@router.get("/patients", response_model=list[PatientResponse])
def list_patients(current_user: CurrentUser, db: DbSession) -> list[Patient]:
    query = db.query(Patient).filter(Patient.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    return query.order_by(Patient.created_at.desc()).all()


@router.post("/patients", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(request: PatientCreate, current_user: CurrentUser, db: DbSession) -> Patient:
    branch_id = request.branch_id or current_user.branch_id or primary_branch(db, current_user.clinic_id).id
    branch = db.query(ClinicBranch).filter(
        ClinicBranch.id == branch_id,
        ClinicBranch.clinic_id == current_user.clinic_id,
    ).first()
    if branch is None or (
        current_user.role == "staff" and current_user.branch_id != branch_id
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Patient branch access denied.")
    patient = Patient(
        clinic_id=current_user.clinic_id,
        branch_id=branch_id,
        **request.model_dump(exclude={"branch_id"}),
    )
    db.add(patient)
    db.flush()
    audit(db, current_user, "create", "patient", patient.id)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/enquiries", response_model=list[PatientEnquiryResponse])
def list_patient_enquiries(
    current_user: CurrentUser,
    db: DbSession,
) -> list[PatientEnquiry]:
    query = db.query(PatientEnquiry).filter(
        PatientEnquiry.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(PatientEnquiry.branch_id == current_user.branch_id)
    enquiries = query.order_by(PatientEnquiry.created_at.desc()).all()
    audit(db, current_user, "access", "patient-enquiries", detail={"count": len(enquiries)})
    db.commit()
    return enquiries


@router.post(
    "/enquiries",
    response_model=PatientEnquiryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient_enquiry(
    request: PatientEnquiryCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientEnquiry:
    branch_id = request.branch_id or current_user.branch_id or primary_branch(
        db, current_user.clinic_id
    ).id
    branch = (
        db.query(ClinicBranch)
        .filter(
            ClinicBranch.id == branch_id,
            ClinicBranch.clinic_id == current_user.clinic_id,
        )
        .first()
    )
    if branch is None or (
        current_user.role == "staff" and current_user.branch_id != branch_id
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Enquiry branch access denied.")
    enquiry = PatientEnquiry(
        clinic_id=current_user.clinic_id,
        branch_id=branch_id,
        **request.model_dump(exclude={"branch_id"}),
    )
    db.add(enquiry)
    db.flush()
    audit(db, current_user, "create", "patient-enquiry", enquiry.id)
    db.commit()
    db.refresh(enquiry)
    return enquiry


@router.patch("/enquiries/{enquiry_id}", response_model=PatientEnquiryResponse)
def update_patient_enquiry(
    enquiry_id: str,
    request: PatientEnquiryUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientEnquiry:
    query = db.query(PatientEnquiry).filter(
        PatientEnquiry.id == enquiry_id,
        PatientEnquiry.clinic_id == current_user.clinic_id,
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(PatientEnquiry.branch_id == current_user.branch_id)
    enquiry = query.first()
    if enquiry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient enquiry not found.")
    transitions = {
        "new": {"contacted", "closed"},
        "contacted": {"consultation-booked", "closed"},
        "consultation-booked": {"closed"},
        "closed": set(),
    }
    if request.status != enquiry.status and request.status not in transitions[enquiry.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot change enquiry status from {enquiry.status} to {request.status}.",
        )
    enquiry.status = request.status
    audit(db, current_user, "update", "patient-enquiry", enquiry.id, {"status": request.status})
    db.commit()
    db.refresh(enquiry)
    return enquiry


@router.post(
    "/enquiries/{enquiry_id}/convert",
    response_model=PatientEnquiryResponse,
)
def convert_patient_enquiry(
    enquiry_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientEnquiry:
    query = db.query(PatientEnquiry).filter(
        PatientEnquiry.id == enquiry_id,
        PatientEnquiry.clinic_id == current_user.clinic_id,
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(PatientEnquiry.branch_id == current_user.branch_id)
    enquiry = query.first()
    if enquiry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient enquiry not found.")
    if enquiry.status not in {"new", "contacted", "consultation-booked"}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only open enquiries can be converted to patients.",
        )
    patient = Patient(
        clinic_id=current_user.clinic_id,
        branch_id=enquiry.branch_id,
        full_name=enquiry.full_name,
        email=enquiry.email,
        phone=enquiry.phone,
        consent_channel="email" if enquiry.email else "phone",
    )
    db.add(patient)
    db.flush()
    enquiry.patient_id = patient.id
    enquiry.status = "converted"
    audit(
        db,
        current_user,
        "convert",
        "patient-enquiry",
        enquiry.id,
        {"patientId": patient.id},
    )
    db.commit()
    db.refresh(enquiry)
    return enquiry


@router.get(
    "/patients/{patient_id}/communications",
    response_model=list[PatientCommunicationResponse],
)
def list_patient_communications(
    patient_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> list[PatientCommunication]:
    patient = clinic_patient(db, current_user, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    communications = (
        db.query(PatientCommunication)
        .filter(
            PatientCommunication.clinic_id == current_user.clinic_id,
            PatientCommunication.patient_id == patient.id,
        )
        .order_by(PatientCommunication.created_at.desc())
        .all()
    )
    audit(
        db,
        current_user,
        "access",
        "patient-communications",
        patient.id,
        {"count": len(communications)},
    )
    db.commit()
    return communications


@router.post(
    "/patients/{patient_id}/communications",
    response_model=PatientCommunicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient_communication(
    patient_id: str,
    request: PatientCommunicationCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientCommunication:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    patient = clinic_patient(db, current_user, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    # Only include fields that the model accepts
    comm_data = request.model_dump(exclude={"summary"})
    communication = PatientCommunication(
        clinic_id=current_user.clinic_id,
        patient_id=patient.id,
        actor_id=current_user.id,
        status="sent",
        sent_at=datetime.now(timezone.utc),
        **comm_data,
    )
    db.add(communication)
    db.flush()
    audit(db, current_user, "create", "patient-communication", communication.id)
    db.commit()
    db.refresh(communication)
    return communication


@router.post(
    "/patients/{patient_id}/communications/email",
    response_model=EmailOutboxResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def send_patient_email(
    patient_id: str,
    request: PatientEmailCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> EmailOutbox:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    if not request.consent_confirmed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Confirm the patient's email consent before queuing a message.",
        )
    patient = clinic_patient(db, current_user, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    outbox = queue_patient_email(
        db,
        current_user,
        patient,
        request.subject,
        request.body_text,
        datetime.now(timezone.utc),
    )
    db.commit()
    db.refresh(outbox)
    return outbox


@router.get("/email-outbox", response_model=list[EmailOutboxResponse])
def list_email_outbox(
    current_user: CurrentUser,
    db: DbSession,
) -> list[EmailOutbox]:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    query = db.query(EmailOutbox).filter(EmailOutbox.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        query = query.join(Patient, Patient.id == EmailOutbox.patient_id).filter(
            Patient.branch_id == current_user.branch_id
        )
    return query.order_by(EmailOutbox.created_at.desc()).limit(100).all()


@router.get("/visits", response_model=list[PatientVisitResponse])
def list_patient_visits(current_user: CurrentUser, db: DbSession) -> list[PatientVisit]:
    query = db.query(PatientVisit).filter(PatientVisit.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(PatientVisit.branch_id == current_user.branch_id)
    return query.order_by(PatientVisit.created_at.desc()).limit(500).all()


@router.post(
    "/visits",
    response_model=PatientVisitResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient_visit(
    request: PatientVisitCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientVisit:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    patient = clinic_patient(db, current_user, request.patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    branch_id = request.branch_id or patient.branch_id or current_user.branch_id
    if patient.branch_id and branch_id != patient.branch_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The visit branch must match the patient's assigned branch.",
        )
    if branch_id:
        branch = db.query(ClinicBranch).filter(
            ClinicBranch.id == branch_id,
            ClinicBranch.clinic_id == current_user.clinic_id,
        ).first()
        if branch is None or (
            current_user.role == "staff" and current_user.branch_id != branch_id
        ):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Visit branch access denied.")
    visit = PatientVisit(
        clinic_id=current_user.clinic_id,
        branch_id=branch_id,
        actor_id=current_user.id,
        **(
            request.model_dump(exclude={"branch_id"})
            | {
                "scheduled_at": utc_datetime(request.scheduled_at)
                if request.scheduled_at
                else None,
                "completed_at": utc_datetime(request.completed_at)
                if request.completed_at
                else None,
            }
        ),
    )
    db.add(visit)
    db.flush()
    if visit.visit_type == "hygiene" and visit.status == "completed":
        automation = recall_settings(db, current_user.clinic_id)
        add_automatic_reminder(
            db,
            current_user,
            patient,
            "hygiene",
            automation.hygiene_recall_days,
            f"hygiene-visit:{visit.id}",
            "Your clinic recommends scheduling your next hygiene visit.",
        )
    audit(db, current_user, "create", "patient-visit", visit.id)
    db.commit()
    db.refresh(visit)
    return visit


@router.get("/treatment-plans", response_model=list[TreatmentPlanResponse])
def list_treatment_plans(current_user: CurrentUser, db: DbSession) -> list[TreatmentPlanResponse]:
    query = db.query(TreatmentPlan).filter(TreatmentPlan.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        query = query.join(Patient, Patient.id == TreatmentPlan.patient_id).filter(
            Patient.branch_id == current_user.branch_id
        )
    plans = query.order_by(TreatmentPlan.created_at.desc()).all()
    return [serialize_plan(db, plan) for plan in plans]


def serialize_plan(db: DbSession, plan: TreatmentPlan) -> TreatmentPlanResponse:
    stages = db.query(TreatmentStage).filter(TreatmentStage.plan_id == plan.id).order_by(TreatmentStage.created_at.asc()).all()
    return TreatmentPlanResponse.model_validate({
        "id": plan.id,
        "patient_id": plan.patient_id,
        "title": plan.title,
        "notes": plan.notes,
        "clinician_name": plan.clinician_name,
        "status": plan.status,
        "estimated_value": plan.estimated_value,
        "currency": plan.currency,
        "stages": [TreatmentStageResponse.model_validate(stage) for stage in stages],
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    })


@router.post("/treatment-plans", response_model=TreatmentPlanResponse, status_code=status.HTTP_201_CREATED)
def create_treatment_plan(request: TreatmentPlanCreate, current_user: CurrentUser, db: DbSession) -> TreatmentPlanResponse:
    patient = clinic_patient(db, current_user, request.patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    plan = TreatmentPlan(
        clinic_id=current_user.clinic_id,
        patient_id=request.patient_id,
        title=request.title,
        notes=request.notes,
        clinician_name=request.clinician_name,
        estimated_value=request.estimated_value,
        currency=request.currency,
    )
    db.add(plan)
    db.flush()
    for stage_request in request.stages:
        stage_values = stage_request.model_dump()
        if stage_request.status in ("deferred", "declined") and not (stage_request.reason or "").strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "A reason is required for a deferred or declined treatment stage.",
            )
        if stage_request.status == "scheduled":
            scheduled_at = stage_request.scheduled_at
            if scheduled_at is None or scheduled_at.tzinfo is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "A timezone-aware appointment time is required for a scheduled treatment stage.",
                )
            scheduled_at = utc_datetime(scheduled_at)
            if scheduled_at <= datetime.now(timezone.utc):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "A future appointment time is required for a scheduled treatment stage.",
                )
            stage_values["scheduled_at"] = scheduled_at
        if stage_request.status == "completed":
            stage_values["completed_at"] = datetime.now(timezone.utc)
        stage = TreatmentStage(
            clinic_id=current_user.clinic_id,
            plan_id=plan.id,
            **stage_values,
            updated_by=current_user.full_name,
        )
        db.add(stage)
        db.flush()
        if stage.status in ("accepted", "deferred", "declined"):
            db.add(
                TreatmentDecision(
                    clinic_id=current_user.clinic_id,
                    patient_id=patient.id,
                    stage_id=stage.id,
                    decision=stage.status,
                    reason=stage.reason,
                    actor_id=current_user.id,
                    actor_role=current_user.role,
                )
            )
    audit(db, current_user, "create", "treatment-plan", plan.id)
    db.commit()
    db.refresh(plan)
    return serialize_plan(db, plan)


@router.patch("/treatment-stages/{stage_id}", response_model=TreatmentStageResponse)
def update_treatment_stage(stage_id: str, request: TreatmentStageUpdate, current_user: CurrentUser, db: DbSession) -> TreatmentStage:
    query = (
        db.query(TreatmentStage)
        .join(TreatmentPlan, TreatmentPlan.id == TreatmentStage.plan_id)
        .join(Patient, Patient.id == TreatmentPlan.patient_id)
        .filter(
            TreatmentStage.id == stage_id,
            TreatmentStage.clinic_id == current_user.clinic_id,
        )
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    stage = query.first()
    if stage is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treatment stage not found.")
    allowed_transitions = {
        "recommended": {"accepted", "deferred", "declined", "scheduled"},
        "accepted": {"deferred", "declined", "scheduled", "completed"},
        "deferred": {"accepted", "scheduled", "declined"},
        "scheduled": {"completed", "deferred", "declined"},
        "declined": set(),
        "completed": set(),
    }
    if request.status not in allowed_transitions.get(stage.status, set()):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot change treatment stage from {stage.status} to {request.status}.")
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinical decisions require clinic staff access.")
    if request.status in ("deferred", "declined") and not (request.reason or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A reason is required for this patient decision.")
    if request.status == "scheduled":
        scheduled_at = request.scheduled_at or stage.scheduled_at
        if scheduled_at is None or scheduled_at.tzinfo is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "A timezone-aware appointment time is required when scheduling a treatment stage.",
            )
        scheduled_at = scheduled_at.astimezone(timezone.utc)
        if scheduled_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "A future appointment time is required when scheduling a treatment stage.",
            )
        stage.scheduled_at = scheduled_at
    stage.status = request.status
    stage.reason = request.reason
    stage.updated_by = current_user.full_name
    if request.status == "completed":
        stage.completed_at = datetime.now(timezone.utc)
    if request.status in ("accepted", "deferred", "declined"):
        plan = db.get(TreatmentPlan, stage.plan_id)
        if plan is not None:
            db.add(
                TreatmentDecision(
                    clinic_id=current_user.clinic_id,
                    patient_id=plan.patient_id,
                    stage_id=stage.id,
                    decision=request.status,
                    reason=request.reason,
                    actor_id=current_user.id,
                    actor_role=current_user.role,
                )
            )
    if request.status in ("deferred", "completed"):
        plan = db.get(TreatmentPlan, stage.plan_id)
        patient = clinic_patient(db, current_user, plan.patient_id) if plan else None
        if patient is not None:
            automation = recall_settings(db, current_user.clinic_id)
            if request.status == "deferred":
                add_automatic_reminder(
                    db,
                    current_user,
                    patient,
                    "pending-visit",
                    automation.pending_treatment_days,
                    f"treatment-stage:{stage.id}:deferred",
                    "Your clinic would like to follow up on your deferred treatment plan.",
                )
            else:
                add_automatic_reminder(
                    db,
                    current_user,
                    patient,
                    "post-procedure",
                    automation.post_procedure_days,
                    f"treatment-stage:{stage.id}:completed",
                    "Your clinic would like to check in after your recent treatment.",
                )
    audit(db, current_user, "update", "treatment-stage", stage.id, {"status": request.status})
    db.commit()
    db.refresh(stage)
    return stage


@router.get(
    "/patients/{patient_id}/decisions",
    response_model=list[TreatmentDecisionResponse],
)
def list_patient_decisions(
    patient_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> list[TreatmentDecision]:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    patient = clinic_patient(db, current_user, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    decisions = (
        db.query(TreatmentDecision)
        .filter(
            TreatmentDecision.clinic_id == current_user.clinic_id,
            TreatmentDecision.patient_id == patient.id,
        )
        .order_by(TreatmentDecision.created_at.desc())
        .all()
    )
    audit(db, current_user, "access", "patient-decisions", patient.id)
    db.commit()
    return decisions


@router.get("/revenue-recovery", response_model=RevenueRecoverySummary)
def revenue_recovery(current_user: CurrentUser, db: DbSession) -> RevenueRecoverySummary:
    query = (
        db.query(TreatmentStage)
        .join(TreatmentPlan, TreatmentPlan.id == TreatmentStage.plan_id)
        .join(Patient, Patient.id == TreatmentPlan.patient_id)
        .filter(TreatmentStage.clinic_id == current_user.clinic_id)
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    stages = query.all()
    statuses = ("deferred", "declined", "accepted", "completed")
    totals = {name: sum(stage.estimated_value for stage in stages if stage.status == name) for name in statuses}
    now = datetime.now(timezone.utc)
    pending = [stage for stage in stages if stage.status in ("recommended", "accepted", "scheduled")]
    overdue = [
        stage
        for stage in pending
        if stage.scheduled_at is not None and utc_datetime(stage.scheduled_at) < now
    ]
    decision_count = (
        db.query(TreatmentDecision)
        .filter(TreatmentDecision.clinic_id == current_user.clinic_id)
        .count()
    )
    if current_user.role == "staff" and current_user.branch_id:
        decision_count = (
            db.query(TreatmentDecision)
            .join(Patient, Patient.id == TreatmentDecision.patient_id)
            .filter(
                TreatmentDecision.clinic_id == current_user.clinic_id,
                Patient.branch_id == current_user.branch_id,
            )
            .count()
        )
    currency = "INR"
    plan_query = db.query(TreatmentPlan).filter(TreatmentPlan.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        plan_query = plan_query.join(Patient, Patient.id == TreatmentPlan.patient_id).filter(
            Patient.branch_id == current_user.branch_id
        )
    plan = plan_query.first()
    if plan:
        currency = plan.currency
    ledger_query = db.query(TreatmentLedgerEntry).filter(
        TreatmentLedgerEntry.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff" and current_user.branch_id:
        ledger_query = ledger_query.filter(
            TreatmentLedgerEntry.branch_id == current_user.branch_id
        )
    ledger_entries = ledger_query.all()
    if ledger_entries:
        currency = ledger_entries[0].currency
    charges_value = sum(
        (entry.amount for entry in ledger_entries if entry.entry_type == "charge"),
        Decimal("0"),
    )
    payments_received = sum(
        (entry.amount for entry in ledger_entries if entry.entry_type == "payment"),
        Decimal("0"),
    )
    refunds_value = sum(
        (entry.amount for entry in ledger_entries if entry.entry_type == "refund"),
        Decimal("0"),
    )
    net_collected = payments_received - refunds_value
    return RevenueRecoverySummary(
        deferred_value=totals["deferred"],
        declined_value=totals["declined"],
        accepted_value=totals["accepted"],
        completed_value=totals["completed"],
        pending_stage_count=len(pending),
        overdue_stage_count=len(overdue),
        pending_value=sum(stage.estimated_value for stage in pending),
        overdue_value=sum(stage.estimated_value for stage in overdue),
        decision_count=decision_count,
        conversion_rate=(sum(stage.status in ("accepted", "scheduled", "completed") for stage in stages) / len(stages) * 100) if stages else 0,
        completion_rate=(sum(stage.status == "completed" for stage in stages) / len(stages) * 100) if stages else 0,
        currency=currency,
        charges_value=float(charges_value),
        payments_received=float(payments_received),
        refunds_value=float(refunds_value),
        net_collected=float(net_collected),
        outstanding_balance=float(charges_value - net_collected),
        ledger_entry_count=len(ledger_entries),
    )


@router.get(
    "/treatment-ledger",
    response_model=list[TreatmentLedgerEntryResponse],
)
def list_treatment_ledger(
    current_user: CurrentUser,
    db: DbSession,
) -> list[TreatmentLedgerEntry]:
    query = db.query(TreatmentLedgerEntry).filter(
        TreatmentLedgerEntry.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(TreatmentLedgerEntry.branch_id == current_user.branch_id)
    return query.order_by(TreatmentLedgerEntry.created_at.desc()).limit(500).all()


@router.post(
    "/treatment-ledger",
    response_model=TreatmentLedgerEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_treatment_ledger_entry(
    request: TreatmentLedgerEntryCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> TreatmentLedgerEntry:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    patient = clinic_patient(db, current_user, request.patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    branch_id = request.branch_id or patient.branch_id
    if patient.branch_id and branch_id != patient.branch_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The ledger branch must match the patient's assigned branch.",
        )
    if current_user.role == "staff" and branch_id != current_user.branch_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ledger branch access denied.")
    if branch_id and db.query(ClinicBranch.id).filter(
        ClinicBranch.id == branch_id,
        ClinicBranch.clinic_id == current_user.clinic_id,
    ).first() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinic branch not found.")
    stage = None
    plan = None
    if request.stage_id:
        stage = (
            db.query(TreatmentStage)
            .join(TreatmentPlan, TreatmentPlan.id == TreatmentStage.plan_id)
            .filter(
                TreatmentStage.id == request.stage_id,
                TreatmentStage.clinic_id == current_user.clinic_id,
                TreatmentPlan.patient_id == patient.id,
            )
            .first()
        )
        if stage is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Treatment stage not found.")
        plan = db.get(TreatmentPlan, stage.plan_id)
        if plan is not None and request.currency != plan.currency:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Ledger currency must match the linked treatment plan.",
            )
    charge_entry = None
    if request.entry_type == "charge" and request.charge_entry_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A charge cannot be linked to another charge.",
        )
    if request.charge_entry_id:
        charge_entry = (
            db.query(TreatmentLedgerEntry)
            .filter(
                TreatmentLedgerEntry.id == request.charge_entry_id,
                TreatmentLedgerEntry.clinic_id == current_user.clinic_id,
                TreatmentLedgerEntry.patient_id == patient.id,
                TreatmentLedgerEntry.entry_type == "charge",
            )
            .first()
        )
        if charge_entry is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Linked treatment charge not found.")
        if charge_entry.currency != request.currency:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Ledger entry currency must match the linked charge.",
            )
        if request.stage_id and request.stage_id != charge_entry.stage_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Ledger entry treatment stage must match the linked charge.",
            )
        if request.entry_type in ("payment", "refund"):
            expire_stale_payment_orders(db, charge_entry.id)
            pending_order = (
                db.query(PatientPaymentOrder.id)
                .filter(
                    PatientPaymentOrder.charge_entry_id == charge_entry.id,
                    PatientPaymentOrder.status == "created",
                )
                .first()
            )
            if pending_order is not None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "This charge has an open online payment order. Retry after it settles or expires.",
                )
            related_entries = (
                db.query(TreatmentLedgerEntry)
                .filter(
                    TreatmentLedgerEntry.clinic_id == current_user.clinic_id,
                    TreatmentLedgerEntry.charge_entry_id == charge_entry.id,
                )
                .all()
            )
            payments = sum(
                (item.amount for item in related_entries if item.entry_type == "payment"),
                Decimal("0"),
            )
            refunds = sum(
                (item.amount for item in related_entries if item.entry_type == "refund"),
                Decimal("0"),
            )
            if request.entry_type == "payment" and request.amount > charge_entry.amount - payments + refunds:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Payment amount exceeds the linked charge balance.",
                )
            if request.entry_type == "refund" and request.amount > payments - refunds:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Refund amount exceeds payments recorded against the linked charge.",
                )
    existing_currency = (
        db.query(TreatmentLedgerEntry.currency)
        .filter(TreatmentLedgerEntry.clinic_id == current_user.clinic_id)
        .first()
    )
    if existing_currency and request.currency != existing_currency[0]:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A clinic ledger cannot mix currencies.",
        )
    entry_data = request.model_dump(exclude={"branch_id"})
    if charge_entry is not None:
        entry_data["stage_id"] = entry_data["stage_id"] or charge_entry.stage_id
    entry = TreatmentLedgerEntry(
        clinic_id=current_user.clinic_id,
        branch_id=branch_id,
        actor_id=current_user.id,
        **entry_data,
    )
    db.add(entry)
    db.flush()
    audit(
        db,
        current_user,
        "create",
        "treatment-ledger-entry",
        entry.id,
        {"entryType": entry.entry_type, "amount": str(entry.amount), "currency": entry.currency},
    )
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/insurance-claims", response_model=list[InsuranceClaimResponse])
def list_insurance_claims(current_user: CurrentUser, db: DbSession) -> list[InsuranceClaim]:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    query = db.query(InsuranceClaim).filter(InsuranceClaim.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(InsuranceClaim.branch_id == current_user.branch_id)
    return query.order_by(InsuranceClaim.created_at.desc()).limit(500).all()


@router.post(
    "/insurance-claims",
    response_model=InsuranceClaimResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_insurance_claim(
    request: InsuranceClaimCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> InsuranceClaim:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    patient = clinic_patient(db, current_user, request.patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    branch_id = patient.branch_id or current_user.branch_id
    charge = None
    if request.charge_entry_id:
        charge = (
            db.query(TreatmentLedgerEntry)
            .filter(
                TreatmentLedgerEntry.id == request.charge_entry_id,
                TreatmentLedgerEntry.clinic_id == current_user.clinic_id,
                TreatmentLedgerEntry.patient_id == patient.id,
                TreatmentLedgerEntry.entry_type == "charge",
            )
            .first()
        )
        if charge is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Linked treatment charge not found.")
        if charge.currency != request.currency or request.billed_amount > charge.amount:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Claim currency must match the linked charge and billed amount cannot exceed it.",
            )
    existing_currency = (
        db.query(TreatmentLedgerEntry.currency)
        .filter(TreatmentLedgerEntry.clinic_id == current_user.clinic_id)
        .first()
    )
    if existing_currency and request.currency != existing_currency[0]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Claim currency must match the clinic ledger.")
    if request.supporting_record_id:
        record = (
            db.query(HealthRecord)
            .filter(
                HealthRecord.id == request.supporting_record_id,
                HealthRecord.clinic_id == current_user.clinic_id,
                HealthRecord.patient_id == patient.id,
            )
            .first()
        )
        if record is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Supporting patient record not found.")

    claim = InsuranceClaim(
        clinic_id=current_user.clinic_id,
        branch_id=branch_id,
        actor_id=current_user.id,
        **request.model_dump(),
    )
    db.add(claim)
    db.flush()
    audit(
        db,
        current_user,
        "create",
        "insurance-claim",
        claim.id,
        {"payer": claim.payer_name, "billedAmount": str(claim.billed_amount)},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The claim could not be saved; check for a duplicate payer claim number.",
        ) from exc
    db.refresh(claim)
    return claim


@router.patch("/insurance-claims/{claim_id}", response_model=InsuranceClaimResponse)
def update_insurance_claim(
    claim_id: str,
    request: InsuranceClaimUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> InsuranceClaim:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    query = (
        db.query(InsuranceClaim)
        .join(Patient, Patient.id == InsuranceClaim.patient_id)
        .filter(
            InsuranceClaim.id == claim_id,
            InsuranceClaim.clinic_id == current_user.clinic_id,
        )
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    claim = query.with_for_update().first()
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Insurance claim not found.")
    if request.status not in INSURANCE_CLAIM_TRANSITIONS[claim.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot change insurance claim from {claim.status} to {request.status}.",
        )
    approved_amount = (
        request.approved_amount
        if request.approved_amount is not None
        else claim.approved_amount
    )
    paid_amount = request.paid_amount if request.paid_amount is not None else claim.paid_amount
    if paid_amount < claim.paid_amount:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Recorded insurance payments cannot decrease.")
    if approved_amount is not None and approved_amount > claim.billed_amount:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Approved amount exceeds the billed amount.")
    if paid_amount > 0 and (approved_amount is None or paid_amount > approved_amount):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Insurance payments cannot exceed the approved claim amount.",
        )
    if request.status == "approved" and approved_amount != claim.billed_amount:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Record the full billed amount as approved, or use partially-approved.",
        )
    if request.status == "partially-approved" and not (
        approved_amount is not None
        and Decimal("0") < approved_amount < claim.billed_amount
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Partially approved claims need an approved amount below the billed amount.",
        )
    if request.status == "denied" and not request.denial_reason.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A denial reason is required.")
    if request.status == "partially-paid" and not (
        paid_amount > 0 and approved_amount is not None and paid_amount < approved_amount
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Partially paid claims require a positive payment below the approved amount.",
        )
    if request.status == "paid" and not (
        approved_amount is not None and paid_amount == approved_amount and paid_amount > 0
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A paid claim must have the full approved amount recorded as paid.",
        )

    payment_delta = paid_amount - claim.paid_amount
    if payment_delta > 0:
        charge = None
        if claim.charge_entry_id:
            charge = db.get(TreatmentLedgerEntry, claim.charge_entry_id)
            if charge is None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "The treatment charge linked to this insurance claim is unavailable.",
                )
        if charge is not None:
            expire_stale_payment_orders(db, charge.id)
            pending_order = (
                db.query(PatientPaymentOrder.id)
                .filter(
                    PatientPaymentOrder.charge_entry_id == charge.id,
                    PatientPaymentOrder.status == "created",
                )
                .first()
            )
            if pending_order is not None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "This charge has an open online payment order. Retry after it settles or expires.",
                )
            related_entries = (
                db.query(TreatmentLedgerEntry)
                .filter(TreatmentLedgerEntry.charge_entry_id == charge.id)
                .all()
            )
            payments = sum(
                (item.amount for item in related_entries if item.entry_type == "payment"),
                Decimal("0"),
            )
            refunds = sum(
                (item.amount for item in related_entries if item.entry_type == "refund"),
                Decimal("0"),
            )
            if payment_delta > charge.amount - payments + refunds:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Insurance payment exceeds the linked charge balance.",
                )
        db.add(
            TreatmentLedgerEntry(
                clinic_id=claim.clinic_id,
                branch_id=claim.branch_id,
                patient_id=claim.patient_id,
                stage_id=charge.stage_id if charge else None,
                charge_entry_id=claim.charge_entry_id,
                entry_type="payment",
                amount=payment_delta,
                currency=claim.currency,
                method="insurance",
                reference=f"insurance-claim:{claim.id}:paid:{paid_amount}",
                notes=f"Insurance remittance from {claim.payer_name}",
                actor_id=current_user.id,
            )
        )
    claim.status = request.status
    claim.approved_amount = approved_amount
    claim.paid_amount = paid_amount
    claim.denial_reason = request.denial_reason.strip()
    if request.notes is not None:
        claim.notes = request.notes.strip()
    if request.status != "draft" and claim.submitted_at is None:
        claim.submitted_at = datetime.now(timezone.utc)
    if request.status in ("paid", "denied", "cancelled"):
        claim.resolved_at = datetime.now(timezone.utc)
    audit(
        db,
        current_user,
        "update",
        "insurance-claim",
        claim.id,
        {
            "status": claim.status,
            "approvedAmount": str(claim.approved_amount) if claim.approved_amount is not None else None,
            "paidAmount": str(claim.paid_amount),
        },
    )
    db.commit()
    db.refresh(claim)
    return claim


@router.get("/analytics", response_model=ClinicPerformanceAnalytics)
def clinic_performance_analytics(
    current_user: CurrentUser,
    db: DbSession,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> ClinicPerformanceAnalytics:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    now = datetime.now(timezone.utc)
    window_end = utc_datetime(to_date) if to_date else now
    window_start = utc_datetime(from_date) if from_date else window_end - timedelta(days=30)
    if window_start >= window_end or (window_end - window_start).days > 366:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Choose a valid analytics range of at most 366 days.",
        )
    stages_query = (
        db.query(TreatmentStage)
        .join(TreatmentPlan, TreatmentPlan.id == TreatmentStage.plan_id)
        .join(Patient, Patient.id == TreatmentPlan.patient_id)
        .filter(TreatmentStage.clinic_id == current_user.clinic_id)
    )
    reminders_query = (
        db.query(RecallReminder)
        .join(Patient, Patient.id == RecallReminder.patient_id)
        .filter(RecallReminder.clinic_id == current_user.clinic_id)
    )
    if current_user.role == "staff" and current_user.branch_id:
        stages_query = stages_query.filter(Patient.branch_id == current_user.branch_id)
        reminders_query = reminders_query.filter(Patient.branch_id == current_user.branch_id)
    stages_query = stages_query.filter(
        TreatmentStage.created_at >= window_start,
        TreatmentStage.created_at < window_end,
    )
    reminders_query = reminders_query.filter(
        RecallReminder.created_at >= window_start,
        RecallReminder.created_at < window_end,
    )
    stages = stages_query.all()
    reminders = reminders_query.all()
    decisions_query = db.query(TreatmentDecision).filter(
        TreatmentDecision.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff" and current_user.branch_id:
        decisions_query = decisions_query.join(
            Patient, Patient.id == TreatmentDecision.patient_id
        ).filter(Patient.branch_id == current_user.branch_id)
    decisions_query = decisions_query.filter(
        TreatmentDecision.created_at >= window_start,
        TreatmentDecision.created_at < window_end,
    )
    visits_query = db.query(PatientVisit).join(
        Patient, Patient.id == PatientVisit.patient_id
    ).filter(
        PatientVisit.clinic_id == current_user.clinic_id,
        PatientVisit.status == "completed",
        PatientVisit.completed_at >= window_start,
        PatientVisit.completed_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        visits_query = visits_query.filter(PatientVisit.branch_id == current_user.branch_id)
    completed_visits = visits_query.all()
    patient_visit_counts: dict[str, int] = {}
    for visit in completed_visits:
        patient_visit_counts[visit.patient_id] = patient_visit_counts.get(visit.patient_id, 0) + 1
    unique_patients_seen = len(patient_visit_counts)
    returning_patients = sum(count > 1 for count in patient_visit_counts.values())
    visits_base_query = db.query(PatientVisit).filter(
        PatientVisit.clinic_id == current_user.clinic_id,
        PatientVisit.created_at >= window_start,
        PatientVisit.created_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        visits_base_query = visits_base_query.filter(
            PatientVisit.branch_id == current_user.branch_id
        )
    open_enquiries_query = db.query(PatientEnquiry).filter(
        PatientEnquiry.clinic_id == current_user.clinic_id,
        PatientEnquiry.created_at >= window_start,
        PatientEnquiry.created_at < window_end,
        PatientEnquiry.status.notin_(("closed", "converted")),
    )
    if current_user.role == "staff" and current_user.branch_id:
        open_enquiries_query = open_enquiries_query.filter(
            PatientEnquiry.branch_id == current_user.branch_id
        )
    completed_stages = sum(stage.status == "completed" for stage in stages)
    completed_followups = sum(reminder.status == "completed" for reminder in reminders)
    overdue_followups = sum(
        reminder.status == "scheduled"
        and utc_datetime(reminder.scheduled_at) < datetime.now(timezone.utc)
        for reminder in reminders
    )
    branch_query = db.query(ClinicBranch).filter(
        ClinicBranch.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff" and current_user.branch_id:
        branch_query = branch_query.filter(ClinicBranch.id == current_user.branch_id)
    pending_approval_query = db.query(RecallReminder).filter(
        RecallReminder.clinic_id == current_user.clinic_id,
        RecallReminder.status == "pending-approval",
        RecallReminder.created_at >= window_start,
        RecallReminder.created_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        pending_approval_query = pending_approval_query.join(
            Patient, Patient.id == RecallReminder.patient_id
        ).filter(Patient.branch_id == current_user.branch_id)
    return ClinicPerformanceAnalytics(
        total_treatment_stages=len(stages),
        accepted_stages=sum(stage.status in ("accepted", "scheduled", "completed") for stage in stages),
        completed_stages=completed_stages,
        open_followups=sum(reminder.status == "scheduled" for reminder in reminders),
        overdue_followups=overdue_followups,
        completed_followups=completed_followups,
        workflow_completion_rate=(completed_stages / len(stages) * 100) if stages else 0,
        followup_completion_rate=(completed_followups / len(reminders) * 100) if reminders else 0,
        decision_count=decisions_query.count(),
        branch_count=branch_query.count(),
        completed_visits=len(completed_visits),
        unique_patients_seen=unique_patients_seen,
        returning_patients=returning_patients,
        patient_retention_rate=(
            returning_patients / unique_patients_seen * 100 if unique_patients_seen else 0
        ),
        no_show_visits=visits_base_query.filter(PatientVisit.status == "no-show").count(),
        scheduled_visits=visits_base_query.filter(
            PatientVisit.status == "scheduled"
        ).count(),
        open_enquiries=open_enquiries_query.count(),
        pending_reminder_approvals=pending_approval_query.count(),
        from_date=window_start,
        to_date=window_end,
    )


@router.get("/records", response_model=list[HealthRecordResponse])
def list_records(current_user: CurrentUser, db: DbSession) -> list[HealthRecord]:
    query = (
        db.query(HealthRecord)
        .join(Patient, Patient.id == HealthRecord.patient_id)
        .filter(HealthRecord.clinic_id == current_user.clinic_id)
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    records = query.order_by(HealthRecord.created_at.desc()).all()
    audit(db, current_user, "access", "health-records", detail={"count": len(records)})
    db.commit()
    return records


def _record_snapshot(record: HealthRecord) -> dict:
    return {
        "recordId": record.id,
        "patientId": record.patient_id,
        "recordCreatedAt": record.created_at.isoformat(),
        "versionNumber": record.version_number,
        "recordType": record.record_type,
        "title": record.title,
        "sourceName": record.source_name,
        "authorName": record.author_name,
        "documentUrl": record.document_url,
        "metadataJson": record.metadata_json,
        "originalFilename": record.original_filename,
        "mimeType": record.mime_type,
        "fileSizeBytes": record.file_size_bytes,
        "fileSha256": record.file_sha256,
    }


def _provenance_hash(snapshot: dict) -> str:
    return sha256(json.dumps(snapshot, sort_keys=True, default=str).encode("utf-8")).hexdigest()


@router.post("/records", response_model=HealthRecordResponse, status_code=status.HTTP_201_CREATED)
def create_record(request: HealthRecordCreate, current_user: CurrentUser, db: DbSession) -> HealthRecord:
    patient = clinic_patient(db, current_user, request.patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    record = HealthRecord(
        clinic_id=current_user.clinic_id,
        version_number=1,
        provenance_hash="",
        **request.model_dump(),
    )
    db.add(record)
    db.flush()
    snapshot = _record_snapshot(record)
    record.provenance_hash = _provenance_hash(snapshot)
    db.add(
        HealthRecordRevision(
            clinic_id=current_user.clinic_id,
            record_id=record.id,
            revision_number=1,
            snapshot=snapshot,
            correction_reason="Original record",
            actor_id=current_user.id,
        )
    )
    audit(db, current_user, "create", "health-record", record.id)
    db.commit()
    db.refresh(record)
    return record


def _validate_document(content_type: str | None, content: bytes) -> str:
    signatures = {
        "application/pdf": content.startswith(b"%PDF-"),
        "image/jpeg": content.startswith(b"\xff\xd8\xff"),
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": (
            len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
        ),
    }
    if content_type not in signatures or not signatures[content_type]:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Upload a valid PDF, JPEG, PNG, or WebP document.",
        )
    return content_type


@router.post("/records/{record_id}/file", response_model=HealthRecordResponse)
async def upload_record_file(
    record_id: str,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> HealthRecord:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    record = (
        db.query(HealthRecord)
        .join(Patient, Patient.id == HealthRecord.patient_id)
        .filter(
            HealthRecord.id == record_id,
            HealthRecord.clinic_id == current_user.clinic_id,
        )
    )
    if current_user.role == "staff" and current_user.branch_id:
        record = record.filter(Patient.branch_id == current_user.branch_id)
    record = record.first()
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.")
    if record.storage_key:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This record already has a file. Create a corrected record version instead.",
        )
    content = await file.read(settings.max_patient_document_bytes + 1)
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty.")
    if len(content) > settings.max_patient_document_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "The uploaded file exceeds the configured size limit.",
        )
    mime_type = _validate_document(file.content_type, content)
    original_filename = PurePath((file.filename or "patient-record").replace("\\", "/")).name
    object_key = (
        f"clinics/{current_user.clinic_id}/patients/{record.patient_id}/"
        f"records/{record.id}/{uuid4().hex}"
    )
    try:
        storage = S3DocumentStorage()
        storage.put(object_key, content, mime_type)
    except DocumentStorageError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    record.version_number += 1
    record.storage_key = object_key
    record.original_filename = original_filename
    record.mime_type = mime_type
    record.file_size_bytes = len(content)
    record.file_sha256 = sha256(content).hexdigest()
    snapshot = _record_snapshot(record)
    record.provenance_hash = _provenance_hash(snapshot)
    db.add(
        HealthRecordRevision(
            clinic_id=current_user.clinic_id,
            record_id=record.id,
            revision_number=record.version_number,
            snapshot=snapshot,
            correction_reason="Patient file attached",
            actor_id=current_user.id,
        )
    )
    audit(
        db,
        current_user,
        "upload",
        "health-record-file",
        record.id,
        {"mimeType": mime_type, "sizeBytes": len(content)},
    )
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        try:
            storage.delete(object_key)
        except DocumentStorageError:
            logger.exception("Could not remove orphaned S3 object for record %s.", record.id)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Document metadata could not be saved.",
        ) from exc
    db.refresh(record)
    return record


@router.get("/records/{record_id}/download")
def download_record_file(
    record_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> Response:
    record = (
        db.query(HealthRecord)
        .join(Patient, Patient.id == HealthRecord.patient_id)
        .filter(
            HealthRecord.id == record_id,
            HealthRecord.clinic_id == current_user.clinic_id,
        )
    )
    if current_user.role == "staff" and current_user.branch_id:
        record = record.filter(Patient.branch_id == current_user.branch_id)
    record = record.first()
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.")
    if not record.storage_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This record has no stored document.")
    try:
        document = S3DocumentStorage().get(record.storage_key)
    except DocumentStorageError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    audit(db, current_user, "export", "health-record-file", record.id)
    db.commit()
    return attachment_response(document, record.original_filename or record.title)


@router.patch("/records/{record_id}", response_model=HealthRecordResponse)
def correct_record(
    record_id: str,
    request: HealthRecordCorrection,
    current_user: CurrentUser,
    db: DbSession,
) -> HealthRecord:
    query = (
        db.query(HealthRecord)
        .join(Patient, Patient.id == HealthRecord.patient_id)
        .filter(
            HealthRecord.id == record_id,
            HealthRecord.clinic_id == current_user.clinic_id,
        )
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    record = query.first()
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.")
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")

    record.version_number += 1
    for field, value in request.model_dump(exclude_unset=True, exclude={"correction_reason"}).items():
        setattr(record, field, value)
    snapshot = _record_snapshot(record)
    record.provenance_hash = _provenance_hash(snapshot)
    db.add(
        HealthRecordRevision(
            clinic_id=current_user.clinic_id,
            record_id=record.id,
            revision_number=record.version_number,
            snapshot=snapshot,
            correction_reason=request.correction_reason.strip(),
            actor_id=current_user.id,
        )
    )
    audit(
        db,
        current_user,
        "correct",
        "health-record",
        record.id,
        {"version": record.version_number, "reason": request.correction_reason.strip()},
    )
    db.commit()
    db.refresh(record)
    return record


@router.get(
    "/records/{record_id}/revisions",
    response_model=list[HealthRecordRevisionResponse],
)
def list_record_revisions(
    record_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> list[HealthRecordRevision]:
    query = (
        db.query(HealthRecord)
        .join(Patient, Patient.id == HealthRecord.patient_id)
        .filter(
            HealthRecord.id == record_id,
            HealthRecord.clinic_id == current_user.clinic_id,
        )
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    if query.first() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.")
    revisions = (
        db.query(HealthRecordRevision)
        .filter(
            HealthRecordRevision.record_id == record_id,
            HealthRecordRevision.clinic_id == current_user.clinic_id,
        )
        .order_by(HealthRecordRevision.revision_number.desc())
        .all()
    )
    audit(db, current_user, "access", "health-record-revisions", record_id)
    db.commit()
    return revisions


@router.get("/consents", response_model=list[RecordConsentResponse])
def list_consents(current_user: CurrentUser, db: DbSession) -> list[RecordConsent]:
    query = (
        db.query(RecordConsent)
        .join(Patient, Patient.id == RecordConsent.patient_id)
        .filter(RecordConsent.clinic_id == current_user.clinic_id)
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    consents = query.order_by(RecordConsent.created_at.desc()).all()
    audit(db, current_user, "access", "record-consents", detail={"count": len(consents)})
    db.commit()
    return consents


@router.post("/consents", response_model=RecordConsentResponse, status_code=status.HTTP_201_CREATED)
def create_consent(request: RecordConsentCreate, current_user: CurrentUser, db: DbSession) -> RecordConsent:
    patient = clinic_patient(db, current_user, request.patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    if not request.scope:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Consent scope cannot be empty.")
    if request.expires_at is not None and (
        request.expires_at.tzinfo is None
        or utc_datetime(request.expires_at) <= datetime.now(timezone.utc)
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Consent expiry must be in the future.")
    if len(set(request.record_ids)) != len(request.record_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Record IDs must be unique.")
    for record_id in request.record_ids:
        record = db.query(HealthRecord).filter(HealthRecord.id == record_id, HealthRecord.patient_id == request.patient_id, HealthRecord.clinic_id == current_user.clinic_id).first()
        if record is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Record {record_id} is not valid for this patient.")
    consent = RecordConsent(clinic_id=current_user.clinic_id, **request.model_dump())
    db.add(consent)
    db.flush()
    audit(db, current_user, "grant", "record-consent", consent.id)
    db.commit()
    db.refresh(consent)
    return consent


@router.post("/consents/{consent_id}/revoke", response_model=RecordConsentResponse)
def revoke_consent(consent_id: str, current_user: CurrentUser, db: DbSession) -> RecordConsent:
    query = (
        db.query(RecordConsent)
        .join(Patient, Patient.id == RecordConsent.patient_id)
        .filter(
            RecordConsent.id == consent_id,
            RecordConsent.clinic_id == current_user.clinic_id,
        )
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    consent = query.first()
    if consent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consent not found.")
    if consent.revoked_at is None:
        consent.revoked_at = datetime.now(timezone.utc)
        audit(db, current_user, "revoke", "record-consent", consent.id)
    db.commit()
    db.refresh(consent)
    return consent


@router.get("/reminders", response_model=list[RecallReminderResponse])
def list_reminders(current_user: CurrentUser, db: DbSession) -> list[RecallReminder]:
    query = (
        db.query(RecallReminder)
        .join(Patient, Patient.id == RecallReminder.patient_id)
        .filter(RecallReminder.clinic_id == current_user.clinic_id)
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    reminders = query.order_by(RecallReminder.scheduled_at.asc()).all()
    audit(db, current_user, "access", "recall-reminders", detail={"count": len(reminders)})
    db.commit()
    return reminders


@router.get(
    "/recall-settings",
    response_model=RecallAutomationSettingsResponse,
)
def get_recall_settings(
    current_user: CurrentUser,
    db: DbSession,
) -> RecallAutomationSettings:
    settings = recall_settings(db, current_user.clinic_id)
    db.commit()
    db.refresh(settings)
    return settings


@router.put(
    "/recall-settings",
    response_model=RecallAutomationSettingsResponse,
)
def update_recall_settings(
    request: RecallAutomationSettingsUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> RecallAutomationSettings:
    if current_user.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic owner access is required.")
    settings = recall_settings(db, current_user.clinic_id)
    for field, value in request.model_dump().items():
        setattr(settings, field, value)
    audit(db, current_user, "update", "recall-automation-settings")
    db.commit()
    db.refresh(settings)
    return settings


@router.post("/reminders", response_model=RecallReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(request: RecallReminderCreate, current_user: CurrentUser, db: DbSession) -> RecallReminder:
    if not request.consent_confirmed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Patient communication consent must be confirmed.")
    if request.scheduled_at.tzinfo is None or utc_datetime(request.scheduled_at) <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reminder time must be in the future.")
    patient = clinic_patient(db, current_user, request.patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    if request.channel == "email" and not patient.email:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The patient does not have an email address on file.",
        )
    reminder = RecallReminder(
        clinic_id=current_user.clinic_id,
        **(
            request.model_dump()
            | {
                "scheduled_at": utc_datetime(request.scheduled_at),
                "consent_confirmed_by": current_user.id,
                "consent_confirmed_at": datetime.now(timezone.utc),
            }
        ),
    )
    db.add(reminder)
    db.flush()
    if request.channel == "email":
        queue_patient_email(
            db,
            current_user,
            patient,
            f"DentalPilot {request.reminder_type.replace('-', ' ')} reminder",
            f"Hello {patient.full_name},\n\n{request.message.strip()}",
            reminder.scheduled_at,
            reminder.id,
        )
    audit(db, current_user, "schedule", "recall-reminder", reminder.id)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.post(
    "/reminders/{reminder_id}/approve",
    response_model=RecallReminderResponse,
)
def approve_automatic_reminder(
    reminder_id: str,
    request: RecallReminderApproval,
    current_user: CurrentUser,
    db: DbSession,
) -> RecallReminder:
    if not request.consent_confirmed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Confirm the patient's email consent before approving this reminder.",
        )
    query = (
        db.query(RecallReminder)
        .join(Patient, Patient.id == RecallReminder.patient_id)
        .filter(
            RecallReminder.id == reminder_id,
            RecallReminder.clinic_id == current_user.clinic_id,
        )
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    reminder = query.first()
    if reminder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reminder not found.")
    if reminder.status != "pending-approval":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only generated reminders waiting for approval can be approved.",
        )
    if reminder.channel != "email":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This patient has no email address; handle the reminder manually.",
        )
    patient = db.query(Patient).filter(
        Patient.id == reminder.patient_id,
        Patient.clinic_id == current_user.clinic_id,
        Patient.email.is_not(None),
    ).first()
    if patient is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The patient no longer has an email address on file.",
        )
    reminder.consent_confirmed = True
    reminder.consent_confirmed_by = current_user.id
    reminder.consent_confirmed_at = datetime.now(timezone.utc)
    reminder.status = "scheduled"
    queue_patient_email(
        db,
        current_user,
        patient,
        f"DentalPilot {reminder.reminder_type.replace('-', ' ')} reminder",
        f"Hello {patient.full_name},\n\n{reminder.message.strip()}",
        reminder.scheduled_at,
        reminder.id,
    )
    audit(
        db,
        current_user,
        "approve",
        "recall-reminder",
        reminder.id,
        {"consentConfirmed": True},
    )
    db.commit()
    db.refresh(reminder)
    return reminder


@router.patch("/reminders/{reminder_id}", response_model=RecallReminderResponse)
def update_reminder(
    reminder_id: str,
    request: RecallReminderUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> RecallReminder:
    query = (
        db.query(RecallReminder)
        .join(Patient, Patient.id == RecallReminder.patient_id)
        .filter(
            RecallReminder.id == reminder_id,
            RecallReminder.clinic_id == current_user.clinic_id,
        )
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    reminder = query.first()
    if reminder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reminder not found.")
    if reminder.status != "scheduled":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only scheduled reminders can be updated.")
    if request.status == "sent" and reminder.channel == "email":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Email reminders are marked sent by the SMTP outbox worker.",
        )
    reminder.status = request.status
    audit(db, current_user, request.status, "recall-reminder", reminder.id)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("/audit", response_model=list[AuditEventResponse])
def list_audit_events(current_user: CurrentUser, db: DbSession) -> list[AuditEvent]:
    query = db.query(AuditEvent).filter(AuditEvent.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(
            (AuditEvent.branch_id == current_user.branch_id)
            | (AuditEvent.branch_id.is_(None))
        )
    return query.order_by(AuditEvent.created_at.desc()).limit(200).all()


@router.get("/integrations", response_model=list[IntegrationConnectionResponse])
def list_integrations(current_user: CurrentUser, db: DbSession) -> list[IntegrationConnection]:
    return db.query(IntegrationConnection).filter(IntegrationConnection.clinic_id == current_user.clinic_id).order_by(IntegrationConnection.created_at.desc()).all()


@router.post("/integrations", response_model=IntegrationConnectionResponse, status_code=status.HTTP_201_CREATED)
def configure_integration(request: IntegrationConnectionCreate, current_user: CurrentUser, db: DbSession) -> IntegrationConnection:
    payload = request.model_dump()
    payload["configuration_json"] = sanitized_integration_config(payload["configuration_json"])
    payload["status"] = "planned"
    connection = IntegrationConnection(clinic_id=current_user.clinic_id, **payload)
    db.add(connection)
    db.flush()
    audit(db, current_user, "configure", "integration", connection.id)
    db.commit()
    db.refresh(connection)
    return connection


@router.post(
    "/integrations/csv/import",
    response_model=IntegrationSyncResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_patient_csv(
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    field_mapping: str = Form("{}"),
) -> IntegrationSyncJob:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload a CSV file.")
    content = await file.read(5_000_001)
    if len(content) > 5_000_000:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "CSV file exceeds the 5 MB limit.")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV file must use UTF-8 encoding.") from exc

    reader = csv.DictReader(io.StringIO(decoded))
    headers = reader.fieldnames or []
    if not headers:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV file must include a header row.")
    if len(headers) != len(set(headers)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV header names must be unique.")
    mapping = parse_patient_mapping(field_mapping, headers)
    rows = list(reader)
    if len(rows) > 5000:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "CSV file exceeds the 5,000-row limit.")

    branch_id = current_user.branch_id or primary_branch(db, current_user.clinic_id).id
    job = IntegrationSyncJob(
        clinic_id=current_user.clinic_id,
        job_type="csv-patient-import",
        status="running",
        field_mapping=mapping,
        actor_id=current_user.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()
    errors: list[dict] = []
    processed_count = 0
    for row_number, row in enumerate(rows, start=2):
        payload = {
            field: (row.get(source) or "").strip() or None
            for field, source in mapping.items()
        }
        try:
            patient_data = PatientCreate.model_validate(payload)
        except ValidationError:
            errors.append({"row": row_number, "message": "Patient data is invalid."})
            continue
        if patient_data.external_reference:
            duplicate = db.query(Patient.id).filter(
                Patient.clinic_id == current_user.clinic_id,
                Patient.external_reference == patient_data.external_reference,
            ).first()
            if duplicate is not None:
                errors.append({"row": row_number, "message": "External patient reference already exists."})
                continue
        patient = Patient(
            clinic_id=current_user.clinic_id,
            branch_id=branch_id,
            **patient_data.model_dump(exclude={"branch_id"}),
        )
        db.add(patient)
        db.flush()
        processed_count += 1

    job.processed_count = processed_count
    job.failed_count = len(errors)
    job.errors = errors[:100]
    job.status = "completed_with_errors" if errors else "completed"
    job.completed_at = datetime.now(timezone.utc)
    audit(
        db,
        current_user,
        "import",
        "patient-csv",
        job.id,
        {"processed": processed_count, "failed": len(errors)},
    )
    db.commit()
    db.refresh(job)
    return job


@router.get("/integrations/csv/export")
def export_patient_csv(current_user: CurrentUser, db: DbSession) -> StreamingResponse:
    query = db.query(Patient).filter(Patient.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    patients = query.order_by(Patient.created_at.asc()).all()
    output = io.StringIO(newline="")
    columns = [
        "externalReference",
        "fullName",
        "email",
        "phone",
        "dateOfBirth",
        "branchId",
        "createdAt",
    ]
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for patient in patients:
        writer.writerow(
            {
                "externalReference": patient.external_reference or "",
                "fullName": patient.full_name,
                "email": patient.email or "",
                "phone": patient.phone or "",
                "dateOfBirth": patient.date_of_birth or "",
                "branchId": patient.branch_id or "",
                "createdAt": patient.created_at.isoformat(),
            }
        )
    audit(db, current_user, "export", "patient-csv", detail={"count": len(patients)})
    db.commit()
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dentalpilot-patients.csv"'},
    )


@router.get("/integrations/sync-jobs", response_model=list[IntegrationSyncResponse])
def list_sync_jobs(current_user: CurrentUser, db: DbSession) -> list[IntegrationSyncJob]:
    return (
        db.query(IntegrationSyncJob)
        .filter(IntegrationSyncJob.clinic_id == current_user.clinic_id)
        .order_by(IntegrationSyncJob.created_at.desc())
        .limit(100)
        .all()
    )


# Communication Templates
@router.get(
    "/communication-templates",
    response_model=list[CommunicationTemplateResponse],
)
def list_communication_templates(
    current_user: CurrentUser,
    db: DbSession,
    channel: str | None = None,
) -> list[CommunicationTemplate]:
    query = db.query(CommunicationTemplate).filter(
        CommunicationTemplate.clinic_id == current_user.clinic_id,
        CommunicationTemplate.is_active.is_(True),
    )
    if channel:
        query = query.filter(CommunicationTemplate.channel == channel)
    return query.order_by(CommunicationTemplate.created_at.desc()).all()


@router.post(
    "/communication-templates",
    response_model=CommunicationTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_communication_template(
    request: CommunicationTemplateCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> CommunicationTemplate:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    template = CommunicationTemplate(
        clinic_id=current_user.clinic_id,
        created_by=current_user.id,
        **request.model_dump(),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.patch(
    "/communication-templates/{template_id}",
    response_model=CommunicationTemplateResponse,
)
def update_communication_template(
    template_id: str,
    request: CommunicationTemplateUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> CommunicationTemplate:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    template = db.query(CommunicationTemplate).filter(
        CommunicationTemplate.id == template_id,
        CommunicationTemplate.clinic_id == current_user.clinic_id,
    ).first()
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Communication template not found.")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    template.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/communication-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_communication_template(
    template_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    template = db.query(CommunicationTemplate).filter(
        CommunicationTemplate.id == template_id,
        CommunicationTemplate.clinic_id == current_user.clinic_id,
    ).first()
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Communication template not found.")
    template.is_active = False
    template.updated_at = datetime.now(timezone.utc)
    db.commit()


# Communication Outbox
@router.post(
    "/communication-outbox",
    response_model=CommunicationOutboxResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def send_patient_communication(
    request: CommunicationOutboxCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> CommunicationOutbox:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    patient = db.query(Patient).filter(
        Patient.id == request.patient_id,
        Patient.clinic_id == current_user.clinic_id,
    ).first()
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")

    # Verify consent for channel
    consent_map = {"email": "email", "sms": "phone", "whatsapp": "phone", "push": "email"}
    required_field = consent_map.get(request.channel)
    if required_field and not getattr(patient, required_field):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Patient has no {required_field} on file for {request.channel} communication.",
        )

    outbox = CommunicationOutbox(
        clinic_id=current_user.clinic_id,
        patient_id=patient.id,
        channel=request.channel,
        recipient=request.recipient,
        subject=request.subject,
        body=request.body,
        template_id=request.template_id,
        status="pending",
        attempt_count=0,
        max_attempts=3,
        available_at=datetime.now(timezone.utc),
        created_by=current_user.id,
    )
    db.add(outbox)
    db.commit()
    db.refresh(outbox)
    return outbox


@router.get(
    "/communication-outbox",
    response_model=list[CommunicationOutboxResponse],
)
def list_communication_outbox(
    current_user: CurrentUser,
    db: DbSession,
    status: str | None = None,
    patient_id: str | None = None,
    limit: int = 100,
) -> list[CommunicationOutbox]:
    query = db.query(CommunicationOutbox).filter(
        CommunicationOutbox.clinic_id == current_user.clinic_id,
    )
    if status:
        query = query.filter(CommunicationOutbox.status == status)
    if patient_id:
        query = query.filter(CommunicationOutbox.patient_id == patient_id)
    return query.order_by(CommunicationOutbox.created_at.desc()).limit(limit).all()


@router.get(
    "/communication-outbox/{outbox_id}",
    response_model=CommunicationOutboxResponse,
)
def get_communication_outbox(
    outbox_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> CommunicationOutbox:
    outbox = db.query(CommunicationOutbox).filter(
        CommunicationOutbox.id == outbox_id,
        CommunicationOutbox.clinic_id == current_user.clinic_id,
    ).first()
    if outbox is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Communication outbox item not found.")
    return outbox
