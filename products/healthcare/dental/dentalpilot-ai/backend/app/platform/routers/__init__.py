"""Platform routers package - shared across all specialty products.

These re-export from existing routers to maintain backwards compatibility
while establishing the platform architecture pattern.
"""

# Platform routers (tenant, identity, consent, audit, patient, document, communication, billing)
from app.routers.auth import router as auth_router
from app.routers.clinic import router as clinic_router
from app.routers.healthcare import router as healthcare_router
from app.routers.patient_portal import router as patient_portal_router
from app.routers.patient_billing import router as patient_billing_router
from app.routers.organizations import router as organizations_router
from app.routers.billing import router as billing_router
from app.routers.integrations import router as integrations_router
from app.routers.dashboard import router as dashboard_router
from app.routers.export import router as export_router

__all__ = [
    "auth_router",
    "clinic_router",
    "healthcare_router",
    "patient_portal_router",
    "patient_billing_router",
    "organizations_router",
    "billing_router",
    "integrations_router",
    "dashboard_router",
    "export_router",
]