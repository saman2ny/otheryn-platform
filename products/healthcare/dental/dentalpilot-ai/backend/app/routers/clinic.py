import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession, RequireOwner
from app.core.security import hash_password
from app.models.clinic import Clinic
from app.models.healthcare import AuditEvent, ClinicBranch, StaffInvitation
from app.models.user import User
from app.schemas.clinic import (
    ClinicBranchCreate,
    ClinicBranchResponse,
    ClinicClinicalAiSettingsResponse,
    ClinicClinicalAiSettingsUpdate,
    ClinicProfile,
    OnboardingStatus,
    StaffInvitationAccept,
    StaffInvitationCreate,
    StaffInvitationResponse,
    StaffMemberResponse,
    UpdateClinicProfileRequest,
)

router = APIRouter(prefix="/clinic", tags=["clinic"])


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@router.get("/profile", response_model=ClinicProfile)
def get_profile(current_user: CurrentUser) -> ClinicProfile:
    return ClinicProfile.model_validate(current_user.clinic)


@router.put("/profile", response_model=ClinicProfile)
def update_profile(request: UpdateClinicProfileRequest, current_user: RequireOwner, db: DbSession) -> ClinicProfile:
    clinic = current_user.clinic
    for field, value in request.model_dump().items():
        setattr(clinic, field, value)
    db.commit()
    db.refresh(clinic)
    return ClinicProfile.model_validate(clinic)


def _clinical_ai_settings(clinic: Clinic) -> ClinicClinicalAiSettingsResponse:
    return ClinicClinicalAiSettingsResponse(
        enabled=clinic.clinical_note_drafting_enabled,
        available=(
            settings.clinical_note_drafting_enabled
            and settings.clinical_ai_data_processing_approved
            and bool(settings.xai_api_key)
        ),
    )


@router.get("/clinical-ai-settings", response_model=ClinicClinicalAiSettingsResponse)
def get_clinical_ai_settings(current_user: CurrentUser) -> ClinicClinicalAiSettingsResponse:
    return _clinical_ai_settings(current_user.clinic)


@router.patch("/clinical-ai-settings", response_model=ClinicClinicalAiSettingsResponse)
def update_clinical_ai_settings(
    request: ClinicClinicalAiSettingsUpdate,
    current_user: RequireOwner,
    db: DbSession,
) -> ClinicClinicalAiSettingsResponse:
    clinic = current_user.clinic
    available = (
        settings.clinical_note_drafting_enabled
        and settings.clinical_ai_data_processing_approved
        and bool(settings.xai_api_key)
    )
    if request.enabled and not available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Clinical note drafting is unavailable until the provider, data-processing approval, and feature flags are configured.",
        )
    clinic.clinical_note_drafting_enabled = request.enabled
    db.add(
        AuditEvent(
            clinic_id=clinic.id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="enable" if request.enabled else "disable",
            resource_type="clinical-note-ai",
            resource_id=clinic.id,
        )
    )
    db.commit()
    db.refresh(clinic)
    return _clinical_ai_settings(clinic)


@router.get("/branches", response_model=list[ClinicBranchResponse])
def list_branches(current_user: CurrentUser, db: DbSession) -> list[ClinicBranch]:
    query = db.query(ClinicBranch).filter(ClinicBranch.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(ClinicBranch.id == current_user.branch_id)
    return query.order_by(ClinicBranch.is_primary.desc(), ClinicBranch.name.asc()).all()


@router.post("/branches", response_model=ClinicBranchResponse, status_code=status.HTTP_201_CREATED)
def create_branch(
    request: ClinicBranchCreate,
    current_user: RequireOwner,
    db: DbSession,
) -> ClinicBranch:
    name = request.name.strip()
    if len(name) < 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Branch name must contain at least two characters.")
    existing = db.query(ClinicBranch).filter(
        ClinicBranch.clinic_id == current_user.clinic_id,
        ClinicBranch.name.ilike(name),
    ).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A branch with this name already exists.")
    is_first_branch = db.query(ClinicBranch.id).filter(
        ClinicBranch.clinic_id == current_user.clinic_id
    ).first() is None
    branch = ClinicBranch(
        clinic_id=current_user.clinic_id,
        name=name,
        address=request.address.strip(),
        phone=request.phone.strip(),
        is_primary=is_first_branch,
    )
    db.add(branch)
    db.flush()
    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="create",
            resource_type="clinic-branch",
            resource_id=branch.id,
        )
    )
    db.commit()
    db.refresh(branch)
    return branch


@router.get("/staff", response_model=list[StaffMemberResponse])
def list_staff(current_user: CurrentUser, db: DbSession) -> list[User]:
    query = db.query(User).filter(User.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(User.branch_id == current_user.branch_id)
    return query.order_by(User.created_at.asc()).all()


@router.post(
    "/staff/invitations",
    response_model=StaffInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_staff(
    request: StaffInvitationCreate,
    current_user: RequireOwner,
    db: DbSession,
) -> StaffInvitationResponse:
    email = str(request.email).lower()
    branch = db.query(ClinicBranch).filter(
        ClinicBranch.id == request.branch_id,
        ClinicBranch.clinic_id == current_user.clinic_id,
    ).first()
    if branch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinic branch not found.")
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    pending = db.query(StaffInvitation).filter(
        StaffInvitation.clinic_id == current_user.clinic_id,
        StaffInvitation.email == email,
        StaffInvitation.accepted_at.is_(None),
        StaffInvitation.expires_at > datetime.now(timezone.utc),
    ).first()
    if pending is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A pending invitation already exists.")

    token = secrets.token_urlsafe(32)
    invitation = StaffInvitation(
        clinic_id=current_user.clinic_id,
        branch_id=branch.id,
        email=email,
        full_name=request.full_name.strip(),
        role="staff",
        token_hash=_token_hash(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_by=current_user.id,
    )
    db.add(invitation)
    db.flush()
    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            branch_id=branch.id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="invite",
            resource_type="clinic-staff",
            resource_id=invitation.id,
            detail={"email": email, "role": "staff"},
        )
    )
    db.commit()
    return StaffInvitationResponse(
        id=invitation.id,
        email=email,
        full_name=invitation.full_name,
        branch_id=branch.id,
        invitation_token=token,
        expires_at=invitation.expires_at,
    )


@router.post("/staff/invitations/accept", status_code=status.HTTP_204_NO_CONTENT)
def accept_staff_invitation(request: StaffInvitationAccept, db: DbSession) -> None:
    invitation = db.query(StaffInvitation).filter(
        StaffInvitation.token_hash == _token_hash(request.invitation_token)
    ).first()
    now = datetime.now(timezone.utc)
    if (
        invitation is None
        or invitation.accepted_at is not None
        or _utc(invitation.expires_at) <= now
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation is invalid or expired.")
    if db.query(User).filter(User.email == invitation.email).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

    user = User(
        email=invitation.email,
        hashed_password=hash_password(request.password),
        full_name=invitation.full_name,
        role=invitation.role,
        clinic_id=invitation.clinic_id,
        branch_id=invitation.branch_id,
    )
    db.add(user)
    db.flush()
    invitation.accepted_at = now
    db.add(
        AuditEvent(
            clinic_id=invitation.clinic_id,
            branch_id=invitation.branch_id,
            actor_id=user.id,
            actor_type="staff",
            action="accept",
            resource_type="staff-invitation",
            resource_id=invitation.id,
        )
    )
    db.commit()


@router.get("/onboarding", response_model=OnboardingStatus)
def onboarding_status(current_user: CurrentUser, db: DbSession) -> OnboardingStatus:
    clinic = current_user.clinic
    profile_complete = all(
        value.strip()
        for value in (clinic.name, clinic.phone, clinic.address, clinic.city, clinic.country)
    )
    branch_count = db.query(ClinicBranch).filter(
        ClinicBranch.clinic_id == current_user.clinic_id
    ).count()
    staff_count = db.query(User).filter(
        User.clinic_id == current_user.clinic_id,
        User.role == "staff",
    ).count()
    subscription_active = clinic.subscription_status in ("active", "trialing")
    
    steps = [
        OnboardingStep(
            id="profile",
            name="Clinic Profile",
            description="Set up your clinic name, contact details, and branding",
            completed=profile_complete,
            required=True,
            order=1,
        ),
        OnboardingStep(
            id="branch",
            name="Clinic Branch",
            description="Create at least one branch location",
            completed=branch_count > 0,
            required=True,
            order=2,
        ),
        OnboardingStep(
            id="staff",
            name="Staff Members",
            description="Invite your team members",
            completed=staff_count > 0,
            required=False,
            order=3,
        ),
        OnboardingStep(
            id="subscription",
            name="Subscription Plan",
            description="Choose a plan that fits your needs",
            completed=subscription_active,
            required=False,
            order=4,
        ),
        OnboardingStep(
            id="integrations",
            name="Integrations",
            description="Connect your practice management system and other tools",
            completed=False,
            required=False,
            order=5,
        ),
    ]
    
    current_step = 1
    for step in steps:
        if not step.completed and step.required:
            break
        current_step += 1
    if current_step > len(steps):
        current_step = len(steps)
    
    required_steps = [s for s in steps if s.required]
    can_complete = all(s.completed for s in required_steps) and clinic.onboarding_completed_at is None
    
    return OnboardingStatus(
        current_step=current_step,
        total_steps=len(steps),
        steps=steps,
        profile_complete=profile_complete,
        branch_count=branch_count,
        staff_count=staff_count,
        subscription_active=subscription_active,
        onboarding_completed_at=clinic.onboarding_completed_at,
        can_complete=can_complete,
    )


@router.post("/onboarding/complete", response_model=OnboardingStatus)
def complete_onboarding(current_user: RequireOwner, db: DbSession) -> OnboardingStatus:
    clinic = current_user.clinic
    if not all(value.strip() for value in (clinic.name, clinic.phone, clinic.address, clinic.city, clinic.country)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Complete the clinic profile before finishing setup.")
    if db.query(ClinicBranch).filter(ClinicBranch.clinic_id == clinic.id).count() == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Create a clinic branch before finishing setup.")
    if clinic.onboarding_completed_at is None:
        clinic.onboarding_completed_at = datetime.now(timezone.utc)
        db.add(
            AuditEvent(
                clinic_id=clinic.id,
                actor_id=current_user.id,
                actor_type=current_user.role,
                action="complete",
                resource_type="clinic-onboarding",
                resource_id=clinic.id,
            )
        )
        db.commit()
        db.refresh(clinic)
    return onboarding_status(current_user, db)
