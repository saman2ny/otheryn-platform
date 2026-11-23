import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from razorpay.errors import BadRequestError, GatewayError, ServerError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession, RequireOwner
from app.models.billing import BillingWebhookEvent, ClinicSubscription, Invoice as InvoiceModel
from app.models.clinic import Clinic
from app.models.healthcare import AuditEvent
from app.schemas.billing import (
    CreateOrderRequest,
    CreateOrderResponse,
    Invoice,
    Subscription,
    SubscriptionPlan,
    SubscriptionCancellationRequest,
    SubscriptionCheckoutRequest,
    SubscriptionCheckoutResponse,
    VerifyPaymentRequest,
    VerifySubscriptionRequest,
)
from app.services import razorpay_service
from app.services.razorpay_service import RazorpayNotConfiguredError

router = APIRouter(prefix="/billing", tags=["billing"])

_PLANS: list[SubscriptionPlan] = [
    SubscriptionPlan(
        tier="free",
        name="Free",
        monthly_price=0,
        annual_price=0,
        ai_credits_per_month=10,
        features=["10 AI content generations / month", "1 clinic profile", "Community support"],
    ),
    SubscriptionPlan(
        tier="starter",
        name="Starter",
        monthly_price=29,
        annual_price=290,
        ai_credits_per_month=50,
        features=["50 AI content generations / month", "Content calendar", "Email support"],
    ),
    SubscriptionPlan(
        tier="professional",
        name="Professional",
        monthly_price=79,
        annual_price=790,
        ai_credits_per_month=200,
        features=["200 AI content generations / month", "Export to PDF/PNG/CSV", "Priority support"],
    ),
    SubscriptionPlan(
        tier="enterprise",
        name="Enterprise",
        monthly_price=199,
        annual_price=1990,
        ai_credits_per_month=1000,
        features=["1000 AI content generations / month", "Multi-clinic management", "Dedicated support"],
    ),
]

_CREDITS_BY_TIER = {plan.tier: plan.ai_credits_per_month for plan in _PLANS}


def _to_subscription(clinic: Clinic, billing: ClinicSubscription | None = None) -> Subscription:
    status_value = clinic.subscription_status
    plan_tier = clinic.plan_tier
    billing_cycle = clinic.billing_cycle
    current_period_end = clinic.current_period_end
    grace_period_ends_at = clinic.grace_period_ends_at
    cancel_at_cycle_end = False
    failure_count = 0
    razorpay_subscription_id = None
    if billing is not None:
        status_value = {
            "creating": "created",
            "creation_failed": "created",
            "authenticated": "authenticated",
            "created": "created",
            "pending": "past_due",
            "halted": "past_due",
            "cancelled": "canceled",
            "completed": "canceled",
            "expired": "canceled",
        }.get(billing.status, billing.status)
        plan_tier = billing.plan_tier
        billing_cycle = billing.billing_cycle
        current_period_end = billing.current_period_end or clinic.current_period_end
        grace_period_ends_at = billing.grace_period_ends_at
        cancel_at_cycle_end = billing.cancel_at_cycle_end
        failure_count = billing.payment_failure_count
        razorpay_subscription_id = billing.razorpay_subscription_id
    return Subscription(
        plan_tier=plan_tier,  # type: ignore[arg-type]
        status=status_value,  # type: ignore[arg-type]
        billing_cycle=billing_cycle,  # type: ignore[arg-type]
        current_period_end=current_period_end,
        grace_period_ends_at=grace_period_ends_at,
        cancel_at_cycle_end=cancel_at_cycle_end,
        payment_failure_count=failure_count,
        razorpay_subscription_id=razorpay_subscription_id,
        ai_credits_used=clinic.ai_credits_used,
        ai_credits_limit=clinic.ai_credits_limit,
    )


def _current_billing(db: Session, clinic_id: str) -> ClinicSubscription | None:
    return (
        db.query(ClinicSubscription)
        .filter(ClinicSubscription.clinic_id == clinic_id, ClinicSubscription.is_current.is_(True))
        .first()
    )


def _webhook_signature_valid(secret: str, raw_body: bytes, signature: str) -> bool:
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.get("/plans", response_model=list[SubscriptionPlan])
def get_plans() -> list[SubscriptionPlan]:
    return _PLANS


@router.get("/subscription", response_model=Subscription)
def get_subscription(current_user: CurrentUser, db: DbSession) -> Subscription:
    return _to_subscription(current_user.clinic, _current_billing(db, current_user.clinic_id))


@router.get("/invoices", response_model=list[Invoice])
def get_invoices(current_user: CurrentUser, db: DbSession) -> list[InvoiceModel]:
    return (
        db.query(InvoiceModel)
        .filter(InvoiceModel.clinic_id == current_user.clinic_id)
        .order_by(InvoiceModel.issued_at.desc())
        .limit(250)
        .all()
    )


@router.post("/subscriptions", response_model=SubscriptionCheckoutResponse)
def create_subscription(
    request: SubscriptionCheckoutRequest,
    current_user: RequireOwner,
    db: DbSession,
) -> SubscriptionCheckoutResponse:
    clinic = current_user.clinic
    current = _current_billing(db, clinic.id)
    if request.plan_tier == "free":
        if current is not None and current.status not in {"cancelled", "completed", "expired", "suspended"}:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Cancel the paid subscription first. The free plan applies when cancellation is confirmed.",
            )
        if current is not None:
            current.is_current = False
        clinic.plan_tier = "free"
        clinic.billing_cycle = request.billing_cycle
        clinic.subscription_status = "active"
        clinic.ai_credits_limit = _CREDITS_BY_TIER["free"]
        clinic.ai_credits_used = min(clinic.ai_credits_used, clinic.ai_credits_limit)
        clinic.grace_period_ends_at = None
        db.commit()
        return SubscriptionCheckoutResponse(
            requires_payment=False,
            subscription=_to_subscription(clinic),
        )

    if current is not None and current.status not in {
        "cancelled",
        "completed",
        "expired",
        "suspended",
        "creation_failed",
    }:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A subscription is already active or awaiting confirmation for this clinic.",
        )
    plan_id = settings.razorpay_plan_ids.get(request.plan_tier, {}).get(request.billing_cycle)
    if not plan_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "This recurring plan is not configured in the Razorpay account.",
        )

    try:
        provider_subscription = razorpay_service.create_subscription(
            plan_id=plan_id,
            total_count=120 if request.billing_cycle == "monthly" else 10,
            clinic_id=clinic.id,
            plan_tier=request.plan_tier,
            billing_cycle=request.billing_cycle,
        )
    except RazorpayNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Razorpay subscription billing is not configured.") from exc
    except (BadRequestError, GatewayError, ServerError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Unable to create a Razorpay subscription.") from exc

    if not provider_subscription.get("id"):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Razorpay did not return a subscription identifier.")
    if current is not None:
        current.is_current = False
    billing = ClinicSubscription(
        clinic_id=clinic.id,
        razorpay_subscription_id=provider_subscription["id"],
        razorpay_plan_id=plan_id,
        plan_tier=request.plan_tier,
        billing_cycle=request.billing_cycle,
        status=provider_subscription.get("status", "created"),
        short_url=provider_subscription.get("short_url"),
    )
    db.add(billing)
    db.add(
        AuditEvent(
            clinic_id=clinic.id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="create",
            resource_type="saas-subscription",
            resource_id=provider_subscription["id"],
            detail={"planTier": request.plan_tier, "billingCycle": request.billing_cycle},
        )
    )
    db.commit()
    db.refresh(billing)
    return SubscriptionCheckoutResponse(
        requires_payment=True,
        subscription=_to_subscription(clinic, billing),
        razorpay_subscription_id=billing.razorpay_subscription_id,
        key_id=settings.razorpay_key_id,
        short_url=billing.short_url,
    )


@router.post("/subscriptions/verify", response_model=Subscription)
def verify_subscription_checkout(
    request: VerifySubscriptionRequest,
    current_user: RequireOwner,
    db: DbSession,
) -> Subscription:
    billing = (
        db.query(ClinicSubscription)
        .filter(
            ClinicSubscription.clinic_id == current_user.clinic_id,
            ClinicSubscription.razorpay_subscription_id == request.razorpay_subscription_id,
            ClinicSubscription.is_current.is_(True),
        )
        .with_for_update()
        .first()
    )
    if billing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription checkout not found.")
    try:
        signature_valid = razorpay_service.verify_subscription_signature(
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_subscription_id=billing.razorpay_subscription_id or "",
            razorpay_signature=request.razorpay_signature,
        )
    except RazorpayNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Razorpay subscription billing is not configured.") from exc
    if not signature_valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Subscription checkout verification failed.")

    billing.checkout_signature_verified_at = datetime.now(timezone.utc)
    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="verify",
            resource_type="saas-subscription-checkout",
            resource_id=billing.razorpay_subscription_id,
            detail={"activationRequiresWebhook": True},
        )
    )
    db.commit()
    return _to_subscription(current_user.clinic, billing)


@router.post("/subscriptions/cancel", response_model=Subscription)
def cancel_subscription(
    request: SubscriptionCancellationRequest,
    current_user: RequireOwner,
    db: DbSession,
) -> Subscription:
    billing = _current_billing(db, current_user.clinic_id)
    if billing is None or billing.razorpay_subscription_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No current paid subscription was found.")
    if billing.status in {"cancelled", "completed", "expired", "creation_failed"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "This subscription can no longer be cancelled.")
    try:
        result = razorpay_service.cancel_subscription(
            billing.razorpay_subscription_id,
            cancel_at_cycle_end=request.cancel_at_cycle_end,
        )
    except RazorpayNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Razorpay subscription billing is not configured.") from exc
    except (BadRequestError, GatewayError, ServerError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Razorpay could not cancel the subscription.") from exc

    billing.cancel_at_cycle_end = bool(result.get("cancel_at_cycle_end"))
    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="request-cancellation",
            resource_type="saas-subscription",
            resource_id=billing.razorpay_subscription_id,
            detail={"cancelAtCycleEnd": billing.cancel_at_cycle_end},
        )
    )
    db.commit()
    return _to_subscription(current_user.clinic, billing)


@router.post("/subscriptions/pause", response_model=Subscription)
def pause_subscription(current_user: RequireOwner, db: DbSession) -> Subscription:
    billing = _current_billing(db, current_user.clinic_id)
    if billing is None or billing.razorpay_subscription_id is None or billing.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only an active subscription can be paused.")
    try:
        razorpay_service.pause_subscription(billing.razorpay_subscription_id)
    except RazorpayNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Razorpay subscription billing is not configured.") from exc
    except (BadRequestError, GatewayError, ServerError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Razorpay could not pause the subscription.") from exc
    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="request-pause",
            resource_type="saas-subscription",
            resource_id=billing.razorpay_subscription_id,
        )
    )
    db.commit()
    return _to_subscription(current_user.clinic, billing)


@router.post("/subscriptions/resume", response_model=Subscription)
def resume_subscription(current_user: RequireOwner, db: DbSession) -> Subscription:
    billing = _current_billing(db, current_user.clinic_id)
    if billing is None or billing.razorpay_subscription_id is None or billing.status != "paused":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a paused subscription can be resumed.")
    try:
        razorpay_service.resume_subscription(billing.razorpay_subscription_id)
    except RazorpayNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Razorpay subscription billing is not configured.") from exc
    except (BadRequestError, GatewayError, ServerError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Razorpay could not resume the subscription.") from exc
    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="request-resume",
            resource_type="saas-subscription",
            resource_id=billing.razorpay_subscription_id,
        )
    )
    db.commit()
    return _to_subscription(current_user.clinic, billing)


@router.post("/razorpay/order", response_model=CreateOrderResponse, include_in_schema=False)
def create_order(
    request: CreateOrderRequest,
    current_user: RequireOwner,
) -> CreateOrderResponse:
    raise HTTPException(
        status.HTTP_410_GONE,
        "One-time SaaS orders are retired. Use recurring subscription checkout.",
    )


@router.post("/razorpay/verify", response_model=Subscription, include_in_schema=False)
def verify_payment(
    request: VerifyPaymentRequest,
    current_user: RequireOwner,
) -> Subscription:
    raise HTTPException(
        status.HTTP_410_GONE,
        "One-time SaaS payment verification is retired. Subscription lifecycle changes require verified webhooks.",
    )


@router.post("/razorpay/subscriptions/webhook", status_code=status.HTTP_202_ACCEPTED)
async def razorpay_subscription_webhook(request: Request, db: DbSession) -> dict[str, str]:
    secret = settings.razorpay_webhook_secret
    if not secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Razorpay subscription webhook is not configured.")
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not _webhook_signature_valid(secret, raw_body, signature):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid Razorpay webhook signature.")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid webhook JSON.") from exc

    event_type = payload.get("event")
    if not isinstance(event_type, str) or not event_type.startswith("subscription."):
        return {"status": "ignored"}
    provider_event_id = request.headers.get("X-Razorpay-Event-Id", "").strip()
    if not provider_event_id or len(provider_event_id) > 160:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Razorpay event ID header is required.")

    event_payload = payload.get("payload")
    event_payload = event_payload if isinstance(event_payload, dict) else {}
    subscription_entity = event_payload.get("subscription", {})
    subscription_entity = subscription_entity.get("entity", {}) if isinstance(subscription_entity, dict) else {}
    payment_entity = event_payload.get("payment", {})
    payment_entity = payment_entity.get("entity", {}) if isinstance(payment_entity, dict) else {}
    subscription_id = subscription_entity.get("id") or payment_entity.get("subscription_id")
    if not isinstance(subscription_id, str) or not subscription_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Subscription webhook is missing its subscription ID.")

    invoice_id = payment_entity.get("invoice_id")
    payment_id = payment_entity.get("id")
    sanitized_payload = {
        "subscription": {
            key: subscription_entity[key]
            for key in ("id", "status", "plan_id", "current_start", "current_end", "cancel_at_cycle_end")
            if key in subscription_entity
        },
        "payment": {
            key: payment_entity[key]
            for key in ("id", "invoice_id", "amount", "currency", "status", "error_code")
            if key in payment_entity
        },
    }
    if db.query(BillingWebhookEvent.id).filter(
        BillingWebhookEvent.provider_event_id == provider_event_id
    ).first():
        return {"status": "duplicate"}
    db.add(
        BillingWebhookEvent(
            provider_event_id=provider_event_id,
            event_type=event_type,
            razorpay_subscription_id=subscription_id,
            razorpay_invoice_id=invoice_id if isinstance(invoice_id, str) else None,
            razorpay_payment_id=payment_id if isinstance(payment_id, str) else None,
            payload=sanitized_payload,
            processing_status="pending",
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.query(BillingWebhookEvent.id).filter(
            BillingWebhookEvent.provider_event_id == provider_event_id
        ).first():
            return {"status": "duplicate"}
        raise
    return {"status": "accepted"}
