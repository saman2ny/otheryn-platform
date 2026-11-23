"""DentalPilot specialty product services.

These are dental-specific services that build on the platform foundation.
"""

from app.services.ai_content import generate_content

__all__ = [
    "generate_content",
]