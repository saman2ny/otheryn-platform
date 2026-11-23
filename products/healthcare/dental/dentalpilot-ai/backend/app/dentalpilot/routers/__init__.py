"""DentalPilot specialty product routers.

These re-export from existing routers to maintain backwards compatibility
while establishing the specialty product architecture pattern.
"""

# DentalPilot-specific routers
from app.routers.content import router as content_router
from app.routers.calendar import router as calendar_router
from app.routers.operations import router as operations_router
from app.routers.growth import router as growth_router
from app.routers.financial_analytics import router as financial_analytics_router

__all__ = [
    "content_router",
    "calendar_router",
    "operations_router",
    "growth_router",
    "financial_analytics_router",
]