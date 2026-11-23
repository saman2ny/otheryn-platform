from collections import defaultdict
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func

from app.core.deps import CurrentUser, DbSession, RequireOwner
from app.models.clinic import Clinic
from app.models.healthcare import (
    AuditEvent,
    ClinicBranch,
    Patient,
    PatientVisit,
    TreatmentLedgerEntry,
    TreatmentPlan,
    TreatmentStage,
)
from app.models.organization import ClinicOrganization, OrganizationInvitation, OrganizationMember
from app.models.user import User
from app.schemas.organization import (
    OrganizationAnalytics,
    OrganizationClinicSummary,
    OrganizationCreate,
    OrganizationFinancialSummary,
    OrganizationInvitationAccept,
    OrganizationInvitationCreate,
    OrganizationInvitationResponse,
    OrganizationMemberResponse,
    OrganizationMemberRoleUpdate,
    OrganizationResponse,
)

router = APIRouter(prefix="/organizations", tags=["clinic-organizations"])
INVITATION_TTL = timedelta(days=7)
ORGANIZATION_OWNER = "organization-owner"
ORGANIZATION_ADMIN = "organization-admin"
REPORTING_ROLES = {ORGANIZATION_OWNER, ORGANIZATION_ADMIN, "reporting-only", "clinic-owner"}
MEMBER_ADMIN_ROLES = {ORGANIZATION_OWNER, ORGANIZATION_ADMIN}


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _membership_for_user(db: DbSession, current_user: CurrentUser) -> OrganizationMember:
    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.clinic_id == current_user.clinic_id,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This clinic is not part of an organization.")
    return membership


def _organization_for_user(db: DbSession, current_user: CurrentUser) -> ClinicOrganization:
    membership = _membership_for_user(db, current_user)
    organization = db.get(ClinicOrganization, membership.organization_id)
    if organization is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found.")
    return organization


def _require_member_role(membership: OrganizationMember, allowed_roles: set[str]) -> None:
    if membership.role not in allowed_roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your organization role does not allow this action.")


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    request: OrganizationCreate,
    current_user: RequireOwner,
    db: DbSession,
) -> OrganizationResponse:
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).with_for_update().first()
    if clinic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinic not found.")
    if clinic.organization_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This clinic already belongs to an organization.")
    existing_membership = (
        db.query(OrganizationMember.id)
        .filter(OrganizationMember.user_id == current_user.id)
        .first()
    )
    if existing_membership is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already manage an organization.")
    organization = ClinicOrganization(name=request.name.strip(), owner_user_id=current_user.id)
    db.add(organization)
    db.flush()
    clinic.organization_id = organization.id
    db.add(
        OrganizationMember(
            organization_id=organization.id,
            user_id=current_user.id,
            clinic_id=clinic.id,
            role="organization-owner",
        )
    )
    db.add(
        AuditEvent(
            clinic_id=clinic.id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="create",
            resource_type="clinic-organization",
            resource_id=organization.id,
        )
    )
    db.commit()
    db.refresh(organization)
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        created_at=organization.created_at,
        clinic_count=1,
        current_member_role=ORGANIZATION_OWNER,
    )


@router.get("/current", response_model=OrganizationResponse | None)
def get_current_organization(
    current_user: RequireOwner,
    db: DbSession,
) -> OrganizationResponse | None:
    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.clinic_id == current_user.clinic_id,
        )
        .first()
    )
    if membership is None:
        return None
    organization = db.get(ClinicOrganization, membership.organization_id)
    if organization is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found.")
    clinic_count = (
        db.query(Clinic.id)
        .filter(Clinic.organization_id == organization.id)
        .count()
    )
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        created_at=organization.created_at,
        clinic_count=clinic_count,
        current_member_role=membership.role,
    )


def _financial_summaries(
    db: DbSession,
    clinic_ids: list[str],
) -> tuple[
    dict[str, list[OrganizationFinancialSummary]],
    list[OrganizationFinancialSummary],
]:
    totals: dict[tuple[str, str], defaultdict[str, Decimal]] = {}
    linked_totals: dict[tuple[str, str], defaultdict[str, Decimal]] = {}

    def values_for(
        aggregate: dict[tuple[str, str], defaultdict[str, Decimal]],
        key: tuple[str, str],
    ) -> defaultdict[str, Decimal]:
        if key not in aggregate:
            aggregate[key] = defaultdict(Decimal)
        return aggregate[key]

    rows = (
        db.query(
            TreatmentLedgerEntry.clinic_id,
            TreatmentLedgerEntry.currency,
            TreatmentLedgerEntry.entry_type,
            func.sum(TreatmentLedgerEntry.amount),
        )
        .filter(TreatmentLedgerEntry.clinic_id.in_(clinic_ids))
        .group_by(
            TreatmentLedgerEntry.clinic_id,
            TreatmentLedgerEntry.currency,
            TreatmentLedgerEntry.entry_type,
        )
        .all()
    )
    for clinic_id, currency, entry_type, amount in rows:
        normalized_currency = currency.upper()
        values_for(totals, (clinic_id, normalized_currency))[entry_type] += amount or Decimal("0")

    linked_rows = (
        db.query(
            TreatmentLedgerEntry.clinic_id,
            TreatmentLedgerEntry.currency,
            TreatmentLedgerEntry.entry_type,
            func.sum(TreatmentLedgerEntry.amount),
        )
        .filter(
            TreatmentLedgerEntry.clinic_id.in_(clinic_ids),
            TreatmentLedgerEntry.charge_entry_id.is_not(None),
            TreatmentLedgerEntry.entry_type.in_(("payment", "refund")),
        )
        .group_by(
            TreatmentLedgerEntry.clinic_id,
            TreatmentLedgerEntry.currency,
            TreatmentLedgerEntry.entry_type,
        )
        .all()
    )
    for clinic_id, currency, entry_type, amount in linked_rows:
        normalized_currency = currency.upper()
        values_for(linked_totals, (clinic_id, normalized_currency))[entry_type] += amount or Decimal("0")

    def summary(currency: str, amounts: dict[str, Decimal], clinic_count: int) -> OrganizationFinancialSummary:
        charges = amounts["charge"]
        payments = amounts["payment"]
        refunds = amounts["refund"]
        outstanding = max(
            charges - amounts["linked-payment"] + amounts["linked-refund"],
            Decimal("0"),
        )
        return OrganizationFinancialSummary(
            currency=currency,
            clinic_count=clinic_count,
            charges_value=float(charges),
            payments_received=float(payments),
            refunds_value=float(refunds),
            net_collected=float(payments - refunds),
            outstanding_balance=float(outstanding),
        )

    clinic_currencies: dict[str, list[OrganizationFinancialSummary]] = defaultdict(list)
    group_totals: dict[str, defaultdict[str, Decimal]] = {}
    group_clinics: dict[str, set[str]] = defaultdict(set)
    for (clinic_id, currency), clinic_amounts in totals.items():
        linked_amounts = linked_totals.get((clinic_id, currency), defaultdict(Decimal))
        for key in ("payment", "refund"):
            clinic_amounts[f"linked-{key}"] = linked_amounts[key]
        clinic_currencies[clinic_id].append(summary(currency, clinic_amounts, 1))
        combined = group_totals.setdefault(currency, defaultdict(Decimal))
        for key, amount in clinic_amounts.items():
            combined[key] += amount
        group_clinics[currency].add(clinic_id)

    clinic_financials = {
        clinic_id: sorted(items, key=lambda item: item.currency)
        for clinic_id, items in clinic_currencies.items()
    }
    group_financials = [
        summary(currency, amounts, len(group_clinics[currency]))
        for currency, amounts in sorted(group_totals.items())
    ]
    return clinic_financials, group_financials


@router.get("/current/analytics", response_model=OrganizationAnalytics)
def get_organization_analytics(
    current_user: RequireOwner,
    db: DbSession,
) -> OrganizationAnalytics:
    membership = _membership_for_user(db, current_user)
    _require_member_role(membership, REPORTING_ROLES)
    organization = _organization_for_user(db, current_user)
    clinics = (
        db.query(Clinic)
        .filter(Clinic.organization_id == organization.id)
        .order_by(Clinic.name.asc())
        .all()
    )
    clinic_ids = [clinic.id for clinic in clinics]
    summaries: list[OrganizationClinicSummary] = []
    branch_total = 0
    patient_total = 0
    open_stage_total = 0
    completed_visit_total = 0
    clinic_financials, group_financials = _financial_summaries(db, clinic_ids)
    for clinic in clinics:
        branch_count = db.query(ClinicBranch.id).filter(ClinicBranch.clinic_id == clinic.id).count()
        patient_count = db.query(Patient.id).filter(Patient.clinic_id == clinic.id).count()
        branch_total += branch_count
        patient_total += patient_count
        summaries.append(
            OrganizationClinicSummary(
                clinic_id=clinic.id,
                clinic_name=clinic.name,
                branch_count=branch_count,
                patient_count=patient_count,
                financials=clinic_financials.get(clinic.id, []),
            )
        )
    if clinic_ids:
        open_stage_total = (
            db.query(TreatmentStage.id)
            .join(TreatmentPlan, TreatmentPlan.id == TreatmentStage.plan_id)
            .filter(
                TreatmentPlan.clinic_id.in_(clinic_ids),
                TreatmentStage.status.notin_(("completed", "declined")),
            )
            .count()
        )
        completed_visit_total = (
            db.query(PatientVisit.id)
            .filter(
                PatientVisit.clinic_id.in_(clinic_ids),
                PatientVisit.status == "completed",
            )
            .count()
        )
    for clinic in clinics:
        db.add(
            AuditEvent(
                clinic_id=clinic.id,
                actor_id=current_user.id,
                actor_type=current_user.role,
                action="access",
                resource_type="organization-financial-analytics",
                resource_id=organization.id,
                detail={"requestingClinicId": current_user.clinic_id},
            )
        )
    db.commit()
    return OrganizationAnalytics(
        organization_id=organization.id,
        organization_name=organization.name,
        clinic_count=len(clinics),
        branch_count=branch_total,
        patient_count=patient_total,
        open_treatment_stage_count=open_stage_total,
        completed_visit_count=completed_visit_total,
        clinics=summaries,
        financials=group_financials,
    )


@router.get("/current/members", response_model=list[OrganizationMemberResponse])
def list_organization_members(
    current_user: RequireOwner,
    db: DbSession,
) -> list[OrganizationMemberResponse]:
    membership = _membership_for_user(db, current_user)
    _require_member_role(membership, MEMBER_ADMIN_ROLES)
    organization = _organization_for_user(db, current_user)
    rows = (
        db.query(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .filter(OrganizationMember.organization_id == organization.id)
        .order_by(OrganizationMember.created_at.asc())
        .all()
    )
    return [
        OrganizationMemberResponse(
            user_id=member.user_id,
            clinic_id=member.clinic_id,
            full_name=user.full_name,
            email=user.email,
            role=member.role,
            created_at=member.created_at,
        )
        for member, user in rows
    ]


@router.post(
    "/current/invitations",
    response_model=OrganizationInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_clinic_owner(
    request: OrganizationInvitationCreate,
    current_user: RequireOwner,
    db: DbSession,
) -> OrganizationInvitationResponse:
    membership = _membership_for_user(db, current_user)
    _require_member_role(membership, MEMBER_ADMIN_ROLES)
    organization = _organization_for_user(db, current_user)
    email = str(request.email).lower()
    if email == current_user.email.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invite a different clinic owner.")
    now = datetime.now(timezone.utc)
    invitation = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.organization_id == organization.id,
            OrganizationInvitation.email == email,
        )
        .first()
    )
    if invitation is not None and invitation.accepted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This clinic owner already accepted an invitation.")
    if invitation is not None and _utc(invitation.expires_at) > now:
        raise HTTPException(status.HTTP_409_CONFLICT, "An active invitation already exists.")

    token = secrets.token_urlsafe(32)
    expires_at = now + INVITATION_TTL
    if invitation is None:
        invitation = OrganizationInvitation(
            organization_id=organization.id,
            email=email,
            token_hash=_token_hash(token),
            invited_by=current_user.id,
            expires_at=expires_at,
        )
        db.add(invitation)
    else:
        invitation.token_hash = _token_hash(token)
        invitation.invited_by = current_user.id
        invitation.expires_at = expires_at
    db.flush()
    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="invite",
            resource_type="organization-clinic",
            resource_id=invitation.id,
            detail={"email": email},
        )
    )
    db.commit()
    db.refresh(invitation)
    return OrganizationInvitationResponse(
        id=invitation.id,
        organization_id=organization.id,
        email=email,
        invitation_token=token,
        expires_at=invitation.expires_at,
    )


@router.post("/invitations/accept", status_code=status.HTTP_204_NO_CONTENT)
def accept_organization_invitation(
    request: OrganizationInvitationAccept,
    current_user: RequireOwner,
    db: DbSession,
) -> None:
    invitation = (
        db.query(OrganizationInvitation)
        .filter(OrganizationInvitation.token_hash == _token_hash(request.invitation_token))
        .with_for_update()
        .first()
    )
    now = datetime.now(timezone.utc)
    if (
        invitation is None
        or invitation.accepted_at is not None
        or _utc(invitation.expires_at) <= now
        or invitation.email.lower() != current_user.email.lower()
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation is invalid or expired.")
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).with_for_update().first()
    if clinic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinic not found.")
    if clinic.organization_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This clinic already belongs to an organization.")
    organization = db.get(ClinicOrganization, invitation.organization_id)
    if organization is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found.")
    clinic.organization_id = organization.id
    invitation.accepted_at = now
    invitation.accepted_by = current_user.id
    db.add(
        OrganizationMember(
            organization_id=organization.id,
            user_id=current_user.id,
            clinic_id=clinic.id,
            role="reporting-only",
        )
    )
    db.add(
        AuditEvent(
            clinic_id=clinic.id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="accept",
            resource_type="organization-clinic-invitation",
            resource_id=invitation.id,
        )
    )
    db.commit()


@router.patch(
    "/current/members/{user_id}/role",
    response_model=OrganizationMemberResponse,
)
def update_organization_member_role(
    user_id: str,
    request: OrganizationMemberRoleUpdate,
    current_user: RequireOwner,
    db: DbSession,
) -> OrganizationMemberResponse:
    membership = _membership_for_user(db, current_user)
    _require_member_role(membership, {ORGANIZATION_OWNER})
    organization = _organization_for_user(db, current_user)
    if organization.owner_user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the organization owner can change member roles.")
    target = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == user_id,
        )
        .with_for_update()
        .first()
    )
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization member not found.")
    if target.user_id == organization.owner_user_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "The organization owner's role cannot be changed.")

    target.role = request.role
    target_user = db.get(User, target.user_id)
    if target_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization member account not found.")
    for clinic_id in {current_user.clinic_id, target.clinic_id}:
        db.add(
            AuditEvent(
                clinic_id=clinic_id,
                actor_id=current_user.id,
                actor_type=current_user.role,
                action="update",
                resource_type="organization-member-role",
                resource_id=target.user_id,
                detail={"role": target.role},
            )
        )
    db.commit()
    db.refresh(target)
    return OrganizationMemberResponse(
        user_id=target.user_id,
        clinic_id=target.clinic_id,
        full_name=target_user.full_name,
        email=target_user.email,
        role=target.role,
        created_at=target.created_at,
    )


@router.delete("/current/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_organization_member(
    user_id: str,
    current_user: RequireOwner,
    db: DbSession,
) -> None:
    membership = _membership_for_user(db, current_user)
    _require_member_role(membership, {ORGANIZATION_OWNER})
    organization = _organization_for_user(db, current_user)
    if organization.owner_user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the organization owner can remove members.")
    target = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == user_id,
        )
        .with_for_update()
        .first()
    )
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization member not found.")
    if target.user_id == organization.owner_user_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "The organization owner cannot be removed.")

    target_clinic = db.get(Clinic, target.clinic_id)
    if target_clinic is not None and target_clinic.organization_id == organization.id:
        target_clinic.organization_id = None
    for clinic_id in {current_user.clinic_id, target.clinic_id}:
        db.add(
            AuditEvent(
                clinic_id=clinic_id,
                actor_id=current_user.id,
                actor_type=current_user.role,
                action="remove",
                resource_type="organization-clinic-member",
                resource_id=target.user_id,
            )
        )
    db.query(OrganizationInvitation).filter(
        OrganizationInvitation.organization_id == organization.id,
        OrganizationInvitation.accepted_by == target.user_id,
    ).delete(synchronize_session=False)
    db.delete(target)
    db.commit()


