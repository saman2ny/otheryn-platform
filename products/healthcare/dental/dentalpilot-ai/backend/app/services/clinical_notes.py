import openai

from app.core.config import settings

_client: openai.OpenAI | None = None

_SYSTEM_PROMPT = (
    "Format only the clinician-provided text as a concise dental clinical-note draft. "
    "Use no facts beyond the supplied text. Do not diagnose, infer findings, recommend treatment, "
    "or add clinical advice. Preserve uncertainty and mark unclear or missing information "
    "for clinician review. The output is an unapproved draft for a licensed clinician to edit."
)


class ClinicalNoteGenerationError(RuntimeError):
    pass


def _get_client() -> openai.OpenAI:
    global _client
    if not settings.xai_api_key:
        raise ClinicalNoteGenerationError("The clinical note provider is not configured.")
    if _client is None:
        _client = openai.OpenAI(
            api_key=settings.xai_api_key,
            base_url=settings.xai_base_url,
            timeout=30.0,
            max_retries=3,
        )
    return _client


def generate_clinical_note(clinician_input: str) -> str:
    if not settings.clinical_note_drafting_enabled or not settings.clinical_ai_data_processing_approved:
        raise ClinicalNoteGenerationError("Clinical note drafting is not enabled for this deployment.")
    try:
        response = _get_client().chat.completions.create(
            model=settings.xai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": clinician_input},
            ],
            temperature=0,
            max_tokens=1200,
        )
    except openai.APIError:
        raise ClinicalNoteGenerationError(
            "The clinical note provider could not complete the request."
        ) from None

    content = response.choices[0].message.content if response.choices else None
    draft = (content or "").strip()
    if not draft:
        raise ClinicalNoteGenerationError("The clinical note provider returned an empty draft.")
    return draft