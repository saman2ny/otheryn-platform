from sqlalchemy import func

from fastapi import APIRouter

from app.core.deps import DbSession, RequireSuperAdmin
from app.models.clinic import Clinic
from app.models.user import User
from app.schemas.admin import AdminClinicSummary

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/clinics", response_model=list[AdminClinicSummary])
def list_all_clinics(current_user: RequireSuperAdmin, db: DbSession) -> list[AdminClinicSummary]:
    """Platform-wide view across every clinic — not scoped to the caller's own clinic."""
    rows = (
        db.query(Clinic, func.count(User.id))
        .outerjoin(User, User.clinic_id == Clinic.id)
        .group_by(Clinic.id)
        .order_by(Clinic.created_at.desc())
        .all()
    )
    return [
        AdminClinicSummary(
            id=clinic.id,
            name=clinic.name,
            plan_tier=clinic.plan_tier,  # type: ignore[arg-type]
            subscription_status=clinic.subscription_status,
            user_count=user_count,
            created_at=clinic.created_at,
        )
        for clinic, user_count in rows
    ]
