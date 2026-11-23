from datetime import datetime
from typing import Literal

from app.schemas.common import CamelModel
from app.schemas.content import ContentPlatform

CalendarEventStatus = Literal["scheduled", "published", "missed"]


class CalendarEvent(CamelModel):
    id: str
    content_id: str
    title: str
    platform: ContentPlatform
    scheduled_at: datetime
    status: CalendarEventStatus


class CreateCalendarEventRequest(CamelModel):
    content_id: str
    title: str
    platform: ContentPlatform
    scheduled_at: datetime
