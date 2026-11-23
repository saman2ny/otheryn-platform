import csv
import io
import json
import logging
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IntegrationContext:
    clinic_id: str
    branch_id: str | None
    actor_id: str


@dataclass(frozen=True)
class AdapterDescriptor:
    provider_id: str
    name: str
    integration_type: str
    mode: str
    enabled: bool
    future_candidates: tuple[str, ...] = ()


class IntegrationAdapter(Protocol):
    descriptor: AdapterDescriptor


class IntegrationAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, IntegrationAdapter] = {}

    def register(self, adapter: IntegrationAdapter) -> None:
        provider_id = adapter.descriptor.provider_id
        if provider_id in self._adapters:
            raise ValueError(f"Integration adapter {provider_id!r} is already registered.")
        self._adapters[provider_id] = adapter

    def resolve(self, provider_id: str) -> IntegrationAdapter:
        try:
            return self._adapters[provider_id]
        except KeyError as exc:
            raise LookupError(f"Integration adapter {provider_id!r} is not available.") from exc

    def catalog(self) -> list[AdapterDescriptor]:
        return [
            adapter.descriptor
            for adapter in sorted(
                self._adapters.values(),
                key=lambda registered: (
                    registered.descriptor.integration_type,
                    registered.descriptor.name,
                ),
            )
        ]


class CsvExchangeAdapter:
    descriptor = AdapterDescriptor(
        provider_id="provider-neutral-csv",
        name="Provider-neutral CSV",
        integration_type="data-exchange",
        mode="file-exchange",
        enabled=True,
        future_candidates=("accounting", "pms", "insurance"),
    )

    def parse_rows(
        self,
        context: IntegrationContext,
        content: bytes,
        field_mapping: dict[str, str],
    ) -> list[dict[str, str]]:
        if not context.clinic_id or not context.actor_id:
            raise ValueError("CSV exchange requires clinic and actor context.")
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            headers = set(reader.fieldnames or [])
            if not field_mapping or not set(field_mapping.values()).issubset(headers):
                raise ValueError("CSV mapping references a missing column.")
            return [
                {
                    field: (row.get(header) or "").strip()
                    for field, header in field_mapping.items()
                }
                for row in reader
            ]
        except UnicodeDecodeError as exc:
            raise ValueError("CSV files must be UTF-8 encoded.") from exc


class WhatsAppCloudAdapter:
    """WhatsApp Cloud API adapter for sending template messages."""
    
    descriptor = AdapterDescriptor(
        provider_id="whatsapp-cloud",
        name="WhatsApp Cloud API",
        integration_type="communications",
        mode="api",
        enabled=True,
    )

    def __init__(self) -> None:
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.access_token = settings.whatsapp_access_token
        self.base_url = "https://graph.facebook.com/v20.0"
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.phone_number_id and self.access_token)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: list[dict] | None = None,
    ) -> dict:
        """Send a WhatsApp template message."""
        if not self.is_configured:
            raise RuntimeError("WhatsApp Cloud API not configured. Set WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN.")

        client = await self._get_client()
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        
        if components:
            payload["template"]["components"] = components

        response = await client.post(
            f"/{self.phone_number_id}/messages",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def send_text_message(self, to: str, text: str) -> dict:
        """Send a free-form text message (only allowed within 24h of user message)."""
        if not self.is_configured:
            raise RuntimeError("WhatsApp Cloud API not configured.")

        client = await self._get_client()
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }

        response = await client.post(
            f"/{self.phone_number_id}/messages",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_template_status(self, template_name: str) -> dict:
        """Check the status of a template."""
        if not self.is_configured:
            raise RuntimeError("WhatsApp Cloud API not configured.")

        client = await self._get_client()
        response = await client.get(f"/{self.phone_number_id}/message_templates", params={"name": template_name})
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


REGISTRY = IntegrationAdapterRegistry()
REGISTRY.register(CsvExchangeAdapter())
REGISTRY.register(WhatsAppCloudAdapter())

FUTURE_PROVIDER_CANDIDATES = (
    AdapterDescriptor(
        provider_id="tally",
        name="Tally",
        integration_type="accounting",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="quickbooks",
        name="QuickBooks",
        integration_type="accounting",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="xero",
        name="Xero",
        integration_type="accounting",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="open-dental",
        name="Open Dental",
        integration_type="pms",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="carestack",
        name="CareStack",
        integration_type="pms",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="dentrix",
        name="Dentrix",
        integration_type="pms",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="eaglesoft",
        name="Eaglesoft",
        integration_type="pms",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="india-insurer-tpa",
        name="India insurers and TPAs",
        integration_type="insurance",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="twilio",
        name="Twilio",
        integration_type="communications",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="google-business-profile",
        name="Google Business Profile",
        integration_type="marketing",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="meta",
        name="Meta",
        integration_type="marketing",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="dicom",
        name="DICOM-compatible imaging",
        integration_type="imaging",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="digital-dentistry",
        name="Scanner, CAD/CAM, and lab systems",
        integration_type="digital-dentistry",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="dental-equipment-iot",
        name="Dental equipment and IoT",
        integration_type="equipment",
        mode="planned",
        enabled=False,
    ),
    AdapterDescriptor(
        provider_id="dental-robotics",
        name="Dental robotics",
        integration_type="robotics",
        mode="planned",
        enabled=False,
    ),
)
