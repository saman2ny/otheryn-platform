from datetime import datetime
from typing import Literal

from app.schemas.common import CamelModel

ExportFormat = Literal["pdf", "png", "csv"]
ExportStatus = Literal["pending", "processing", "completed", "failed"]


class ExportRequest(CamelModel):
    content_ids: list[str]
    format: ExportFormat


class ExportJob(CamelModel):
    id: str
    format: ExportFormat
    status: ExportStatus
    content_ids: list[str]
    download_url: str | None = None
    created_at: datetime
