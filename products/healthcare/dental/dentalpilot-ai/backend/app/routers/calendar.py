from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.models.calendar import CalendarEvent as CalendarEventModel
from app.schemas.calendar import CalendarEvent, CreateCalendarEventRequest

router = APIRouter(prefix="/calendar/events", tags=["calendar"])


@router.get("", response_model=list[CalendarEvent])
def list_events(current_user: CurrentUser, db: DbSession) -> list[CalendarEventModel]:
    return (
        db.query(CalendarEventModel)
        .filter(CalendarEventModel.clinic_id == current_user.clinic_id)
        .order_by(CalendarEventModel.scheduled_at.asc())
        .all()
    )


@router.post("", response_model=CalendarEvent)
def create_event(request: CreateCalendarEventRequest, current_user: CurrentUser, db: DbSession) -> CalendarEventModel:
    event = CalendarEventModel(
        clinic_id=current_user.clinic_id,
        content_id=request.content_id,
        title=request.title,
        platform=request.platform,
        scheduled_at=request.scheduled_at,
        status="scheduled",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_event(event_id: str, current_user: CurrentUser, db: DbSession) -> None:
    event = (
        db.query(CalendarEventModel)
        .filter(CalendarEventModel.id == event_id, CalendarEventModel.clinic_id == current_user.clinic_id)
        .first()
    )
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found.")
    db.delete(event)
    db.commit()
    return None
