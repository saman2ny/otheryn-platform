import anthropic

from app.core.config import settings

_client: anthropic.Anthropic | None = None

_SYSTEM_PROMPT = (
    "Format only the clinician-provided text as a concise dental clinical-note draft. "
    "Use no facts beyond the supplied text. Do not diagnose, infer findings, recommend treatment, "
    "or add clinical advice. Preserve uncertainty and mark unclear or missing information "
    "for clinician review. The output is an unapproved draft for a licensed clinician to edit."
)


class ClinicalNoteGenerationError(RuntimeError):
    pass


def _get_client() -> anthropic.Anthropic:
    global _client
    if not settings.anthropic_api_key:
        raise ClinicalNoteGenerationError("The clinical note provider is not configured.")
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)
    return _client


def generate_clinical_note(clinician_input: str) -> str:
    if not settings.clinical_note_drafting_enabled or not settings.clinical_ai_data_processing_approved:
        raise ClinicalNoteGenerationError("Clinical note drafting is not enabled for this deployment.")
    try:
        response = _get_client().messages.create(
            model=settings.anthropic_model,
            max_tokens=1200,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": clinician_input}],
        )
    except anthropic.APIError as exc:
        raise ClinicalNoteGenerationError("The clinical note provider could not complete the request.") from exc

    text_blocks = [block.text.strip() for block in response.content if block.type == "text" and block.text.strip()]
    draft = "\n".join(text_blocks).strip()
    if not draft:
        raise ClinicalNoteGenerationError("The clinical note provider returned an empty draft.")
    return draft
