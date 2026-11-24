from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.models.content import GeneratedContent as GeneratedContentModel
from app.schemas.content import GenerateContentRequest, GeneratedContent
from app.services.ai_content import AiNotConfiguredError, AiProviderError, generate_content

router = APIRouter(prefix="/content", tags=["content"])


@router.post("/generate", response_model=GeneratedContent)
def generate(request: GenerateContentRequest, current_user: CurrentUser, db: DbSession) -> GeneratedContent:
    clinic = current_user.clinic
    grace_end = clinic.grace_period_ends_at
    if grace_end is not None and grace_end.tzinfo is None:
        grace_end = grace_end.replace(tzinfo=timezone.utc)
    if clinic.plan_tier != "free" and (
        clinic.subscription_status in {"suspended", "paused"}
        or (
            clinic.subscription_status == "past_due"
            and (grace_end is None or grace_end <= datetime.now(timezone.utc))
        )
    ):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Subscription access is suspended. Update the payment method or reactivate the subscription.",
        )
    if clinic.ai_credits_used >= clinic.ai_credits_limit:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"AI credit limit reached ({clinic.ai_credits_limit}/month on the {clinic.plan_tier} plan). "
            "Upgrade your plan for more credits.",
        )
    try:
        generated = generate_content(clinic, request)
    except AiNotConfiguredError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI content generation is not configured. Set GROQ_API_KEY on the backend.",
        ) from exc
    except AiProviderError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "The AI provider could not generate content. Please try again shortly.",
        ) from exc

    record = GeneratedContentModel(
        clinic_id=clinic.id,
        platform=request.platform,
        tone=request.tone,
        topic=request.topic,
        headline=generated["headline"],
        body=generated["body"],
        hashtags=generated["hashtags"],
        image_prompt_suggestion=generated.get("image_prompt_suggestion"),
        status="ready",
    )
    db.add(record)
    clinic.ai_credits_used += 1
    db.commit()
    db.refresh(record)
    return GeneratedContent.model_validate(record)


@router.get("", response_model=list[GeneratedContent])
def list_content(current_user: CurrentUser, db: DbSession) -> list[GeneratedContentModel]:
    return (
        db.query(GeneratedContentModel)
        .filter(GeneratedContentModel.clinic_id == current_user.clinic_id)
        .order_by(GeneratedContentModel.created_at.desc())
        .all()
    )


@router.get("/{content_id}", response_model=GeneratedContent)
def get_content(content_id: str, current_user: CurrentUser, db: DbSession) -> GeneratedContentModel:
    record = (
        db.query(GeneratedContentModel)
        .filter(GeneratedContentModel.id == content_id, GeneratedContentModel.clinic_id == current_user.clinic_id)
        .first()
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content not found.")
    return record
