from datetime import datetime
from typing import Literal

from app.schemas.common import CamelModel

ContentPlatform = Literal["instagram", "facebook", "google-business", "blog", "sms"]
ContentTone = Literal["friendly", "professional", "premium", "playful", "educational"]
ContentStatus = Literal["draft", "ready", "scheduled", "published"]


class GenerateContentRequest(CamelModel):
    topic: str
    platform: ContentPlatform
    tone: ContentTone
    treatment: str | None = None
    include_hashtags: bool
    include_call_to_action: bool


class GeneratedContent(CamelModel):
    id: str
    platform: ContentPlatform
    tone: ContentTone
    topic: str
    headline: str
    body: str
    hashtags: list[str]
    image_prompt_suggestion: str | None = None
    status: ContentStatus
    created_at: datetime
