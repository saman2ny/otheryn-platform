import json
import logging
from typing import Any

import openai

from app.core.config import settings
from app.models.clinic import Clinic
from app.schemas.content import GenerateContentRequest

logger = logging.getLogger(__name__)

_client: openai.OpenAI | None = None


class AiNotConfiguredError(RuntimeError):
    pass


class AiProviderError(RuntimeError):
    pass


def _get_client() -> openai.OpenAI:
    global _client
    if not settings.xai_api_key:
        raise AiNotConfiguredError("XAI_API_KEY is not set.")
    if _client is None:
        _client = openai.OpenAI(
            api_key=settings.xai_api_key,
            base_url=settings.xai_base_url,
            timeout=30.0,
            max_retries=3,
        )
    return _client


def _map_provider_error(exc: Exception) -> AiProviderError:
    if isinstance(exc, openai.RateLimitError):
        return AiProviderError("The AI provider is rate-limited. Please try again shortly.")
    if isinstance(exc, openai.AuthenticationError):
        return AiProviderError("The AI provider rejected the credentials.")
    if isinstance(exc, openai.APITimeoutError):
        return AiProviderError("The AI provider timed out.")
    if isinstance(exc, openai.APIConnectionError):
        return AiProviderError("The AI provider is unreachable.")
    if isinstance(exc, openai.APIStatusError):
        return AiProviderError(f"The AI provider returned an error ({exc.status_code}).")
    return AiProviderError("The AI provider could not complete the request.")


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


def _validate_output(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise AiProviderError("The AI provider returned an invalid response shape.")
    for key, expected in (
        ("headline", str),
        ("body", str),
        ("hashtags", list),
        ("image_prompt_suggestion", str),
    ):
        if key not in data or not isinstance(data[key], expected):
            raise AiProviderError("The AI provider returned an invalid response shape.")
    if not all(isinstance(tag, str) for tag in data["hashtags"]):
        raise AiProviderError("The AI provider returned an invalid response shape.")
    return data


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
        + "\n\nReturn a JSON object with exactly these keys: "
        + '"headline" (string), "body" (string), "hashtags" (array of strings), '
        + '"image_prompt_suggestion" (string).'
    )

    try:
        response = client.chat.completions.create(
            model=settings.xai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1024,
        )
    except openai.APIError as exc:
        logger.warning("AI content request failed: %s status=%s", type(exc).__name__, getattr(exc, "status_code", None))
        raise _map_provider_error(exc) from exc

    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise AiProviderError("The AI provider returned an empty response.")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AiProviderError("The AI provider returned malformed JSON.") from exc
    return _validate_output(parsed)