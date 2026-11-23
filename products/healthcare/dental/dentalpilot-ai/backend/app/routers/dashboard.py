from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.models.calendar import CalendarEvent
from app.models.content import GeneratedContent
from app.schemas.dashboard import DashboardContentItem, DashboardEventItem, DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(current_user: CurrentUser, db: DbSession) -> DashboardSummary:
    clinic = current_user.clinic
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    content_this_month = (
        db.query(GeneratedContent)
        .filter(GeneratedContent.clinic_id == clinic.id, GeneratedContent.created_at >= month_start)
        .count()
    )
    upcoming_count = (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.clinic_id == clinic.id,
            CalendarEvent.status == "scheduled",
            CalendarEvent.scheduled_at >= now,
        )
        .count()
    )
    recent_content = (
        db.query(GeneratedContent)
        .filter(GeneratedContent.clinic_id == clinic.id)
        .order_by(GeneratedContent.created_at.desc())
        .limit(5)
        .all()
    )
    upcoming_events = (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.clinic_id == clinic.id,
            CalendarEvent.status == "scheduled",
            CalendarEvent.scheduled_at >= now,
        )
        .order_by(CalendarEvent.scheduled_at.asc())
        .limit(5)
        .all()
    )

    return DashboardSummary(
        content_generated_this_month=content_this_month,
        posts_scheduled_upcoming=upcoming_count,
        ai_credits_used=clinic.ai_credits_used,
        ai_credits_limit=clinic.ai_credits_limit,
        plan_tier=clinic.plan_tier,  # type: ignore[arg-type]
        recent_content=[
            DashboardContentItem(id=c.id, headline=c.headline, platform=c.platform, created_at=c.created_at)
            for c in recent_content
        ],
        upcoming_events=[
            DashboardEventItem(id=e.id, title=e.title, platform=e.platform, scheduled_at=e.scheduled_at)
            for e in upcoming_events
        ],
    )
