import json
from types import SimpleNamespace

import httpx
import openai
import pytest

from app.core.config import settings
from app.models.clinic import Clinic
from app.schemas.content import GenerateContentRequest
from app.services import ai_content, clinical_notes
from app.services.ai_content import AiNotConfiguredError, AiProviderError, generate_content
from app.services.clinical_notes import ClinicalNoteGenerationError, generate_clinical_note


class _FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class _FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=_FakeCompletions(responses))


def _response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def _clinic():
    return Clinic(
        name="Test Clinic",
        specialty="general-dentistry",
        brand_tone="friendly",
        target_audience="patients",
        about_text="Test clinic",
    )


def _request():
    return GenerateContentRequest(
        topic="Dental implants",
        platform="instagram",
        tone="friendly",
        include_hashtags=True,
        include_call_to_action=True,
    )


def test_generate_content_uses_configured_groq_model(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "groq_model", "llama-3.3-70b-versatile")
    fake = _FakeClient(
        [_response(json.dumps({"headline": "H", "body": "B", "hashtags": ["dental"], "image_prompt_suggestion": "P"}))]
    )
    monkeypatch.setattr(ai_content, "_get_client", lambda: fake)

    result = generate_content(_clinic(), _request())

    assert result["headline"] == "H"
    assert fake.chat.completions.calls[0]["model"] == "llama-3.3-70b-versatile"


def test_generate_content_missing_key(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)

    with pytest.raises(AiNotConfiguredError):
        generate_content(_clinic(), _request())


def test_generate_content_malformed_json(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(ai_content, "_get_client", lambda: _FakeClient([_response("not json")]))

    with pytest.raises(AiProviderError):
        generate_content(_clinic(), _request())


def test_generate_content_invalid_shape(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(ai_content, "_get_client", lambda: _FakeClient([_response(json.dumps({"headline": "H"}))]))

    with pytest.raises(AiProviderError):
        generate_content(_clinic(), _request())


def test_generate_content_rate_limit(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    request = httpx.Request("POST", "https://api.x.ai/v1/chat/completions")
    exc = openai.RateLimitError("rate limited", response=httpx.Response(429, request=request), body=None)
    monkeypatch.setattr(ai_content, "_get_client", lambda: _FakeClient([exc]))

    with pytest.raises(AiProviderError):
        generate_content(_clinic(), _request())


def test_generate_content_timeout(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    request = httpx.Request("POST", "https://api.x.ai/v1/chat/completions")
    monkeypatch.setattr(ai_content, "_get_client", lambda: _FakeClient([openai.APITimeoutError(request=request)]))

    with pytest.raises(AiProviderError):
        generate_content(_clinic(), _request())


def test_generate_content_server_error(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    request = httpx.Request("POST", "https://api.x.ai/v1/chat/completions")
    exc = openai.InternalServerError("server error", response=httpx.Response(500, request=request), body=None)
    monkeypatch.setattr(ai_content, "_get_client", lambda: _FakeClient([exc]))

    with pytest.raises(AiProviderError):
        generate_content(_clinic(), _request())


def test_clinical_note_success(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "clinical_note_drafting_enabled", True)
    monkeypatch.setattr(settings, "clinical_ai_data_processing_approved", True)
    fake = _FakeClient([_response("Draft note")])
    monkeypatch.setattr(clinical_notes, "_get_client", lambda: fake)

    assert generate_clinical_note("Patient reports sensitivity") == "Draft note"
    assert fake.chat.completions.calls[0]["model"] == settings.groq_model


def test_clinical_note_gate(monkeypatch):
    monkeypatch.setattr(settings, "clinical_note_drafting_enabled", False)
    monkeypatch.setattr(settings, "clinical_ai_data_processing_approved", True)

    with pytest.raises(ClinicalNoteGenerationError):
        generate_clinical_note("text")


def test_clinical_note_missing_key(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "clinical_note_drafting_enabled", True)
    monkeypatch.setattr(settings, "clinical_ai_data_processing_approved", True)

    with pytest.raises(ClinicalNoteGenerationError):
        generate_clinical_note("text")