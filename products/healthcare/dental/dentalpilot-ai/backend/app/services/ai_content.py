import json
from typing import Any

import anthropic

from app.core.config import settings
from app.models.clinic import Clinic
from app.schemas.content import GenerateContentRequest

_client: anthropic.Anthropic | None = None


class AiNotConfiguredError(RuntimeError):
    pass


def _get_client() -> anthropic.Anthropic:
    global _client
    if not settings.anthropic_api_key:
        raise AiNotConfiguredError("ANTHROPIC_API_KEY is not set.")
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {
            "type": "string",
            "description": "A short, scroll-stopping headline for the post.",
        },
        "body": {
            "type": "string",
            "description": "The main post copy, ready to publish as-is.",
        },
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Hashtags without the leading #. Empty array if hashtags were not requested.",
        },
        "image_prompt_suggestion": {
            "type": "string",
            "description": "A one-sentence prompt describing an accompanying image for this post.",
        },
    },
    "required": ["headline", "body", "hashtags", "image_prompt_suggestion"],
    "additionalProperties": False,
}


def generate_content(clinic: Clinic, request: GenerateContentRequest) -> dict[str, Any]:
    client = _get_client()

    system = (
        "You are the in-house marketing copywriter for a dental clinic. Write content that is accurate, "
        "compliant with typical healthcare-marketing norms (no guaranteed outcomes, no unverifiable medical "
        "claims), and matches the clinic's brand voice exactly.\n\n"
        f"Clinic: {clinic.name}\n"
        f"Specialty: {clinic.specialty}\n"
        f"Brand tone: {clinic.brand_tone}\n"
        f"Target audience: {clinic.target_audience or 'general local patients'}\n"
        f"About: {clinic.about_text or 'No additional details provided.'}"
    )

    user_prompt = (
        f"Write a {request.platform} post in a {request.tone} tone about: {request.topic}.\n"
        + (f"Relevant treatment: {request.treatment}.\n" if request.treatment else "")
        + (
            "Include 3-6 relevant hashtags (no leading #)."
            if request.include_hashtags
            else "Do not include any hashtags — return an empty array."
        )
        + "\n"
        + (
            "End with a clear call to action to book an appointment."
            if request.include_call_to_action
            else "Do not include a call to action."
        )
    )

    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": _OUTPUT_SCHEMA}},
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text_block = next(block for block in response.content if block.type == "text")
    return json.loads(text_block.text)
