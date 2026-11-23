import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import func

from app.core.deps import CurrentPatient, CurrentUser, DbSession
from app.core.security import (
    create_patient_access_token,
    hash_password,
    verify_password,
)
from app.models.healthcare import (
    AuditEvent,
    HealthRecord,
    Patient,
    PatientPortalAccount,
    PatientRecordShare,
    RecordConsent,
)
from app.schemas.healthcare import (
    PatientResponse,
    PortalInvitationAccept,
    PortalInvitationCreate,
    PortalInvitationResponse,
    PortalLogin,
    PortalLoginResponse,
    PortalShareCreate,
    PortalShareResponse,
    PortalShareView,
)
from app.schemas.healthcare import HealthRecordResponse
from app.services.document_storage import (
    DocumentStorageError,
    S3DocumentStorage,
    attachment_response,
)

router = APIRouter(prefix="/patient-portal", tags=["patient-portal"])


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _patient_for_account(db: DbSession, account: PatientPortalAccount) -> Patient:
    patient = db.query(Patient).filter(
        Patient.id == account.patient_id,
        Patient.clinic_id == account.clinic_id,
    ).first()
    if patient is None or not patient.email or patient.email.lower() != account.email.lower():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Patient portal account is no longer valid.")
    return patient


def _audit_portal(
    db: DbSession,
    patient: Patient,
    account_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            clinic_id=patient.clinic_id,
            branch_id=patient.branch_id,
            actor_id=account_id,
            actor_type="patient",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail or {},
        )
    )


@router.post("/invitations", response_model=PortalInvitationResponse, status_code=status.HTTP_201_CREATED)
def invite_patient(
    request: PortalInvitationCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> PortalInvitationResponse:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")
    query = db.query(Patient).filter(
        Patient.id == request.patient_id,
        Patient.clinic_id == current_user.clinic_id,
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(Patient.branch_id == current_user.branch_id)
    patient = query.first()
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found.")
    if not patient.email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add a patient email before sending an invitation.")

    account = db.query(PatientPortalAccount).filter(
        PatientPortalAccount.patient_id == patient.id
    ).first()
    if account is not None and account.hashed_password is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This patient already has a portal account.")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    if account is None:
        account = PatientPortalAccount(
            clinic_id=patient.clinic_id,
            patient_id=patient.id,
            email=patient.email.lower(),
        )
        db.add(account)
    account.email = patient.email.lower()
    account.invitation_token_hash = _token_hash(token)
    account.invitation_expires_at = expires_at
    db.flush()
    _audit_portal(db, patient, current_user.id, "invite", "patient-portal", account.id)
    db.commit()
    return PortalInvitationResponse(
        invitation_token=token,
        expires_at=expires_at,
        clinic_id=patient.clinic_id,
        email=patient.email,
    )


@router.post("/invitations/accept", status_code=status.HTTP_204_NO_CONTENT)
def accept_invitation(request: PortalInvitationAccept, db: DbSession) -> None:
    account = db.query(PatientPortalAccount).filter(
        PatientPortalAccount.invitation_token_hash == _token_hash(request.invitation_token)
    ).first()
    now = datetime.now(timezone.utc)
    if (
        account is None
        or account.invitation_expires_at is None
        or _utc(account.invitation_expires_at) <= now
        or account.hashed_password is not None
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation is invalid or expired.")

    patient = db.get(Patient, account.patient_id)
    if patient is None or not patient.email or patient.email.lower() != account.email.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Patient email changed; request a new invitation.")

    account.hashed_password = hash_password(request.password)
    account.email_verified_at = now
    account.invitation_token_hash = None
    account.invitation_expires_at = None
    _audit_portal(db, patient, account.id, "activate", "patient-portal", account.id)
    db.commit()


@router.post("/login", response_model=PortalLoginResponse)
def login(request: PortalLogin, db: DbSession) -> PortalLoginResponse:
    account = db.query(PatientPortalAccount).filter(
        PatientPortalAccount.clinic_id == request.clinic_id,
        func.lower(PatientPortalAccount.email) == request.email.lower(),
        PatientPortalAccount.email_verified_at.is_not(None),
        PatientPortalAccount.hashed_password.is_not(None),
    ).first()
    if account is None or not verify_password(request.password, account.hashed_password or ""):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid clinic, email, or password.")
    patient = _patient_for_account(db, account)
    account.last_login_at = datetime.now(timezone.utc)
    _audit_portal(db, patient, account.id, "login", "patient-portal", account.id)
    db.commit()
    return PortalLoginResponse(
        access_token=create_patient_access_token(account.id),
        patient=PatientResponse.model_validate(patient),
    )


@router.get("/me", response_model=PatientResponse)
def get_patient_profile(account: CurrentPatient, db: DbSession) -> PatientResponse:
    patient = _patient_for_account(db, account)
    _audit_portal(db, patient, account.id, "read", "patient-profile", patient.id)
    db.commit()
    return PatientResponse.model_validate(patient)


@router.get("/records", response_model=list[HealthRecordResponse])
def list_patient_records(account: CurrentPatient, db: DbSession) -> list[HealthRecord]:
    patient = _patient_for_account(db, account)
    records = (
        db.query(HealthRecord)
        .filter(
            HealthRecord.patient_id == patient.id,
            HealthRecord.clinic_id == patient.clinic_id,
        )
        .order_by(HealthRecord.created_at.desc())
        .all()
    )
    _audit_portal(db, patient, account.id, "access", "health-records", detail={"count": len(records)})
    db.commit()
    return records


@router.get("/records/{record_id}/download")
def download_patient_record(record_id: str, account: CurrentPatient, db: DbSession) -> Response:
    patient = _patient_for_account(db, account)
    record = db.query(HealthRecord).filter(
        HealthRecord.id == record_id,
        HealthRecord.patient_id == patient.id,
        HealthRecord.clinic_id == patient.clinic_id,
    ).first()
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.")
    if record.storage_key:
        try:
            document = S3DocumentStorage().get(record.storage_key)
        except DocumentStorageError as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
        _audit_portal(db, patient, account.id, "export", "health-record-file", record.id)
        db.commit()
        return attachment_response(document, record.original_filename or record.title)
    payload = HealthRecordResponse.model_validate(record).model_dump(mode="json", by_alias=True)
    _audit_portal(db, patient, account.id, "export", "health-record", record.id)
    db.commit()
    return Response(
        content=json.dumps(payload, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="record-{record.id}.json"'},
    )


@router.get("/shares/{share_token}/records/{record_id}/download")
def download_shared_record(
    share_token: str,
    record_id: str,
    db: DbSession,
) -> Response:
    share = db.query(PatientRecordShare).filter(
        PatientRecordShare.token_hash == _token_hash(share_token)
    ).first()
    now = datetime.now(timezone.utc)
    if share is None or share.revoked_at is not None or _utc(share.expires_at) <= now:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shared records are unavailable.")
    consent = db.query(RecordConsent).filter(
        RecordConsent.id == share.consent_id,
        RecordConsent.clinic_id == share.clinic_id,
    ).first()
    if (
        consent is None
        or consent.revoked_at is not None
        or (consent.expires_at is not None and _utc(consent.expires_at) <= now)
        or "download" not in consent.scope
        or record_id not in consent.record_ids
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shared records are unavailable.")
    record = db.query(HealthRecord).filter(
        HealthRecord.id == record_id,
        HealthRecord.patient_id == consent.patient_id,
        HealthRecord.clinic_id == consent.clinic_id,
    ).first()
    if record is None or not record.storage_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shared document is unavailable.")
    try:
        document = S3DocumentStorage().get(record.storage_key)
    except DocumentStorageError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    patient = db.get(Patient, consent.patient_id)
    if patient is not None:
        _audit_portal(
            db,
            patient,
            None,
            "export",
            "shared-health-record-file",
            record.id,
            {"consentId": consent.id, "recipient": consent.recipient_name},
        )
        db.commit()
    return attachment_response(document, record.original_filename or record.title)


@router.post("/shares", response_model=PortalShareResponse, status_code=status.HTTP_201_CREATED)
def share_patient_records(
    request: PortalShareCreate,
    account: CurrentPatient,
    db: DbSession,
) -> PortalShareResponse:
    patient = _patient_for_account(db, account)
    expires_at = _utc(request.expires_at)
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Share expiry must be in the future.")
    if "view" not in request.scope:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A shared record link must allow viewing.")
    if len(set(request.record_ids)) != len(request.record_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Record IDs must be unique.")

    records = db.query(HealthRecord).filter(
        HealthRecord.id.in_(request.record_ids),
        HealthRecord.patient_id == patient.id,
        HealthRecord.clinic_id == patient.clinic_id,
    ).all()
    if len(records) != len(request.record_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "One or more records are not available to this patient.")

    consent = RecordConsent(
        clinic_id=patient.clinic_id,
        patient_id=patient.id,
        purpose=request.purpose,
        recipient_name=request.recipient_name,
        record_ids=request.record_ids,
        scope=request.scope,
        expires_at=expires_at,
    )
    db.add(consent)
    db.flush()
    token = secrets.token_urlsafe(32)
    db.add(
        PatientRecordShare(
            clinic_id=patient.clinic_id,
            consent_id=consent.id,
            token_hash=_token_hash(token),
            expires_at=expires_at,
        )
    )
    _audit_portal(
        db,
        patient,
        account.id,
        "share",
        "record-consent",
        consent.id,
        {"recipient": request.recipient_name, "record_count": len(records)},
    )
    db.commit()
    return PortalShareResponse(consent_id=consent.id, share_token=token, expires_at=expires_at)


@router.get("/shares/{share_token}", response_model=PortalShareView)
def view_shared_records(share_token: str, db: DbSession) -> PortalShareView:
    share = db.query(PatientRecordShare).filter(
        PatientRecordShare.token_hash == _token_hash(share_token)
    ).first()
    now = datetime.now(timezone.utc)
    if share is None or share.revoked_at is not None or _utc(share.expires_at) <= now:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shared records are unavailable.")
    consent = db.query(RecordConsent).filter(
        RecordConsent.id == share.consent_id,
        RecordConsent.clinic_id == share.clinic_id,
    ).first()
    if (
        consent is None
        or consent.revoked_at is not None
        or (consent.expires_at is not None and _utc(consent.expires_at) <= now)
        or "view" not in consent.scope
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shared records are unavailable.")

    records = db.query(HealthRecord).filter(
        HealthRecord.id.in_(consent.record_ids),
        HealthRecord.patient_id == consent.patient_id,
        HealthRecord.clinic_id == consent.clinic_id,
    ).all()
    patient = db.get(Patient, consent.patient_id)
    if patient is not None:
        _audit_portal(db, patient, None, "access", "shared-records", consent.id)
        db.commit()
    return PortalShareView(
        purpose=consent.purpose,
        recipient_name=consent.recipient_name,
        records=[HealthRecordResponse.model_validate(record) for record in records],
        expires_at=share.expires_at,
    )


@router.post("/shares/{consent_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_patient_share(
    consent_id: str,
    account: CurrentPatient,
    db: DbSession,
) -> None:
    patient = _patient_for_account(db, account)
    consent = db.query(RecordConsent).filter(
        RecordConsent.id == consent_id,
        RecordConsent.patient_id == patient.id,
        RecordConsent.clinic_id == patient.clinic_id,
    ).first()
    if consent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consent not found.")
    if consent.revoked_at is None:
        consent.revoked_at = datetime.now(timezone.utc)
        _audit_portal(db, patient, account.id, "revoke", "record-consent", consent.id)
        db.commit()
