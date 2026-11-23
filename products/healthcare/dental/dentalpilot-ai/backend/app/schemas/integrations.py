from pydantic import Field

from app.schemas.common import CamelModel


class IntegrationCatalogEntry(CamelModel):
    provider_id: str
    name: str
    integration_type: str
    mode: str
    enabled: bool
    future_candidates: list[str] = Field(default_factory=list)
