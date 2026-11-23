from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.schemas.integrations import IntegrationCatalogEntry
from app.services.integration_adapters import FUTURE_PROVIDER_CANDIDATES, REGISTRY

router = APIRouter(prefix="/integrations", tags=["integration-adapters"])


@router.get("/catalog", response_model=list[IntegrationCatalogEntry])
def list_integration_adapters(current_user: CurrentUser) -> list[IntegrationCatalogEntry]:
    descriptors = REGISTRY.catalog() + list(FUTURE_PROVIDER_CANDIDATES)
    return [
        IntegrationCatalogEntry(
            provider_id=descriptor.provider_id,
            name=descriptor.name,
            integration_type=descriptor.integration_type,
            mode=descriptor.mode,
            enabled=descriptor.enabled,
            future_candidates=list(descriptor.future_candidates),
        )
        for descriptor in descriptors
    ]
