"""Platform services package - shared across all specialty products.

These re-export from existing services to maintain backwards compatibility
while establishing the platform architecture pattern.
"""

from app.services.email_delivery import EmailDeliveryError, send_email
from app.services.integration_adapters import REGISTRY, IntegrationContext
from app.services.export_render import render

__all__ = [
    "EmailDeliveryError",
    "send_email",
    "REGISTRY",
    "IntegrationContext",
    "render",
]