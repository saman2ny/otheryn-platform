from datetime import datetime

from app.schemas.common import CamelModel
from app.schemas.user import PlanTier


class AdminClinicSummary(CamelModel):
    id: str
    name: str
    plan_tier: PlanTier
    subscription_status: str
    user_count: int
    created_at: datetime
