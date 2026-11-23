import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from razorpay.errors import BadRequestError, GatewayError, ServerError
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.billing import BillingWebhookEvent, ClinicSubscription, Invoice
from app.models.clinic import Clinic
from app.models.healthcare import AuditEvent
from app.services import razorpay_service
from app.services.razorpay_service import RazorpayNotConfiguredError
from app.services.email_delivery import EmailDeliveryError, send_email

logger = logging.getLogger(__name__)
STALE_CLAIM_MINUTES = 10
MAX_BATCH_SIZE = 25
_CREDITS_BY_TIER = {"free": 10, "starter": 50, "professional": 200, "enterprise": 1000}
_TERMINAL_PROVIDER_STATES = {"cancelled", "completed", "expired"}
_PROVIDER_ERRORS = (
    RazorpayNotConfiguredError,
    BadRequestError,
    GatewayError,
    ServerError,
)
# Dunning configuration
DUNNING_RETRY_DAYS = [1, 3, 5, 7, 14]  # Days after initial failure to retry
MAX_DUNNING_ATTEMPTS = len(DUNNING_RETRY_DAYS)


class BillingEventProcessingError(RuntimeError):
    pass


def _utc_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(timestamp, timezone.utc)


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _local_status(provider_status: str, grace_ends_at: datetime | None) -> str:
    if provider_status == "active":
        return "active"
    if provider_status == "authenticated":
        return "authenticated"
    if provider_status == "created":
        return "created"
    if provider_status == "paused":
        return "paused"
    if provider_status in _TERMINAL_PROVIDER_STATES:
        return "cancelled" if provider_status == "cancelled" else provider_status
    grace_ends_at = _aware_utc(grace_ends_at)
    if provider_status in {"pending", "halted"}:
        if grace_ends_at is not None and grace_ends_at <= datetime.now(timezone.utc):
            return "suspended"
        return "past_due"
    raise BillingEventProcessingError("Razorpay returned an unsupported subscription status.")


def _minor_amount(amount: object, currency: str) -> float:
    try:
        minor_units = int(amount)
    except (TypeError, ValueError) as exc:
        raise BillingEventProcessingError("Razorpay invoice amount is invalid.") from exc
    zero_decimal = {"BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}
    return float(minor_units if currency.upper() in zero_decimal else minor_units / 100)


def _upsert_invoice(db: Session, clinic_id: str, subscription_id: str, invoice_data: dict) -> None:
    external_id = invoice_data.get("id")
    if not isinstance(external_id, str) or not external_id:
        raise BillingEventProcessingError("Razorpay invoice is missing its ID.")
    currency = invoice_data.get("currency")
    if not isinstance(currency, str) or len(currency) != 3:
        raise BillingEventProcessingError("Razorpay invoice currency is invalid.")
    provider_status = invoice_data.get("status")
    status_map = {
        "paid": "paid",
        "issued": "open",
        "partially_paid": "open",
        "draft": "open",
        "cancelled": "void",
        "expired": "void",
    }
    if provider_status not in status_map:
        raise BillingEventProcessingError("Razorpay invoice status is unsupported.")
    amount = invoice_data.get("amount_paid") if provider_status == "paid" else invoice_data.get("amount")
    if amount is None:
        amount = invoice_data.get("amount_due")
    invoice = db.query(Invoice).filter(Invoice.external_invoice_id == external_id).first()
    if invoice is None:
        invoice = Invoice(clinic_id=clinic_id, amount=0, currency=currency.lower(), status="open")
        db.add(invoice)
    invoice.external_invoice_id = external_id
    invoice.razorpay_subscription_id = subscription_id
    invoice.razorpay_payment_id = invoice_data.get("payment_id")
    invoice.amount = _minor_amount(amount, currency)
    invoice.currency = currency.lower()
    invoice.status = status_map[provider_status]
    invoice.download_url = invoice_data.get("short_url")
    invoice.period_start = _utc_datetime(invoice_data.get("period_start"))
    invoice.period_end = _utc_datetime(invoice_data.get("period_end"))
    invoice.issued_at = _utc_datetime(invoice_data.get("issued_at")) or datetime.now(timezone.utc)
    invoice.paid_at = _utc_datetime(invoice_data.get("paid_at")) if provider_status == "paid" else None


def _sync_subscription(
    db: Session,
    billing: ClinicSubscription,
    provider_data: dict,
    event_type: str,
) -> None:
    clinic = db.get(Clinic, billing.clinic_id)
    if clinic is None:
        raise BillingEventProcessingError("The subscription clinic no longer exists.")
    provider_status = provider_data.get("status")
    if not isinstance(provider_status, str):
        raise BillingEventProcessingError("Razorpay subscription status is missing.")

    old_period_end = _aware_utc(billing.current_period_end)
    billing.grace_period_ends_at = _aware_utc(billing.grace_period_ends_at)
    period_start = _utc_datetime(provider_data.get("current_start"))
    period_end = _utc_datetime(provider_data.get("current_end"))
    if period_start is not None:
        billing.current_period_start = period_start
    if period_end is not None:
        billing.current_period_end = period_end
        clinic.current_period_end = period_end
    billing.cancel_at_cycle_end = bool(
        provider_data.get("cancel_at_cycle_end", billing.cancel_at_cycle_end)
    )
    now = datetime.now(timezone.utc)
    if event_type in {"subscription.pending", "subscription.halted"}:
        billing.payment_failure_count += 1
        if billing.grace_period_ends_at is None:
            billing.grace_period_ends_at = now + timedelta(days=settings.subscription_grace_period_days)
    new_status = _local_status(provider_status, billing.grace_period_ends_at)
    if provider_status == "halted" and new_status == "suspended":
        billing.status = "suspended"
    else:
        billing.status = new_status
    billing.last_synced_at = now
    clinic.grace_period_ends_at = billing.grace_period_ends_at

    if billing.status == "active":
        clinic.plan_tier = billing.plan_tier
        clinic.billing_cycle = billing.billing_cycle
        clinic.subscription_status = "active"
        clinic.ai_credits_limit = _CREDITS_BY_TIER[billing.plan_tier]
        clinic.grace_period_ends_at = None
        billing.grace_period_ends_at = None
        billing.payment_failure_count = 0
        if old_period_end is None or (
            billing.current_period_end is not None and billing.current_period_end > old_period_end
        ):
            clinic.ai_credits_used = 0
    elif billing.status == "past_due":
        clinic.subscription_status = "past_due"
    elif billing.status == "paused":
        clinic.subscription_status = "paused"
    elif billing.status == "suspended":
        clinic.subscription_status = "suspended"
    elif billing.status in _TERMINAL_PROVIDER_STATES:
        billing.is_current = False
        clinic.plan_tier = "free"
        clinic.subscription_status = "canceled"
        clinic.ai_credits_limit = _CREDITS_BY_TIER["free"]
        clinic.ai_credits_used = min(clinic.ai_credits_used, clinic.ai_credits_limit)
        clinic.grace_period_ends_at = None

    db.add(
        AuditEvent(
            clinic_id=clinic.id,
            actor_type="system",
            action="webhook-sync",
            resource_type="saas-subscription",
            resource_id=billing.razorpay_subscription_id,
            detail={"eventType": event_type, "status": billing.status},
        )
    )


def _send_dunning_email(
    db: Session,
    clinic: Clinic,
    billing: ClinicSubscription,
    attempt: int,
    invoice_data: dict | None = None,
) -> None:
    """Send dunning email for failed payment."""
    if not settings.smtp_host or not settings.smtp_sender_email:
        logger.warning("SMTP not configured, skipping dunning email for clinic %s", clinic.id)
        return
    
    try:
        subject = f"Payment Failed - Action Required for Your {billing.plan_tier.title()} Plan"
        amount = invoice_data.get("amount_due", 0) if invoice_data else 0
        amount_str = f"{_minor_amount(amount, invoice_data.get('currency', 'USD')):.2f}" if invoice_data else "N/A"
        
        body = f"""Dear {clinic.name} Team,

We attempted to process your subscription payment for the {billing.plan_tier.title()} plan, but the payment failed.

Amount Due: {amount_str} {billing.billing_cycle.title()}
Retry Attempt: {attempt} of {MAX_DUNNING_ATTEMPTS}

Please update your payment method or contact support to resolve this issue. Your subscription will remain active during the grace period ({settings.subscription_grace_period_days} days), but if payment is not received by then, your account may be suspended.

You can update your payment method by logging into your DentalPilot AI account and visiting the Billing section.

If you have already made the payment, please disregard this message.

Best regards,
The DentalPilot AI Team
"""
        
        send_email(
            outbox_id=f"dunning-{billing.id}-{attempt}",
            recipient=clinic.owner_email if hasattr(clinic, 'owner_email') else "admin@dentalpilot.ai",
            subject=subject,
            body_text=body,
        )
        logger.info("Dunning email sent for clinic %s, attempt %d", clinic.id, attempt)
    except EmailDeliveryError as exc:
        logger.error("Failed to send dunning email for clinic %s: %s", clinic.id, exc)


def _process_event(db: Session, event: BillingWebhookEvent) -> None:
    if event.razorpay_subscription_id is None:
        event.processing_status = "ignored"
        event.processed_at = datetime.now(timezone.utc)
        return
    billing = (
        db.query(ClinicSubscription)
        .filter(ClinicSubscription.razorpay_subscription_id == event.razorpay_subscription_id)
        .with_for_update()
        .first()
    )
    if billing is None:
        event.processing_status = "ignored"
        event.processed_at = datetime.now(timezone.utc)
        return
    provider_data = razorpay_service.fetch_subscription(event.razorpay_subscription_id)
    _sync_subscription(db, billing, provider_data, event.event_type)

    invoice_id = event.razorpay_invoice_id
    if invoice_id:
        invoice_data = razorpay_service.fetch_invoice(invoice_id)
        _upsert_invoice(db, billing.clinic_id, event.razorpay_subscription_id, invoice_data)
        
        # Handle dunning for failed payments
        if event.event_type in {"subscription.charged", "invoice.payment_failed"} and invoice_data.get("status") != "paid":
            clinic = db.get(Clinic, billing.clinic_id)
            if clinic:
                _send_dunning_email(db, clinic, billing, billing.payment_failure_count, invoice_data)

    event.processing_status = "processed"
    event.processed_at = datetime.now(timezone.utc)
    event.claimed_at = None
    event.last_error = None


def _fail_event(db: Session, event_id: str, error: Exception) -> None:
    event = db.get(BillingWebhookEvent, event_id)
    if event is None:
        return
    event.last_error = type(error).__name__
    event.claimed_at = None
    if event.attempt_count >= settings.billing_webhook_max_attempts:
        event.processing_status = "failed"
    else:
        event.processing_status = "pending"
        event.available_at = datetime.now(timezone.utc) + timedelta(
            seconds=min(30 * (2 ** max(0, event.attempt_count - 1)), 3600)
        )
    db.commit()
    logger.warning(
        "Subscription webhook processing failed event_id=%s event_type=%s attempt=%s error_type=%s",
        event.provider_event_id,
        event.event_type,
        event.attempt_count,
        type(error).__name__,
    )


def process_billing_webhook_batch(
    session_factory: Callable[[], Session] = SessionLocal,
    batch_size: int = MAX_BATCH_SIZE,
) -> int:
    processed = 0
    for _ in range(min(batch_size, MAX_BATCH_SIZE)):
        with session_factory() as db:
            now = datetime.now(timezone.utc)
            stale_claim = now - timedelta(minutes=STALE_CLAIM_MINUTES)
            candidate = (
                db.query(BillingWebhookEvent.id)
                .filter(
                    or_(
                        (BillingWebhookEvent.processing_status == "pending")
                        & (BillingWebhookEvent.available_at <= now),
                        (BillingWebhookEvent.processing_status == "processing")
                        & (BillingWebhookEvent.claimed_at < stale_claim),
                    )
                )
                .order_by(BillingWebhookEvent.available_at.asc(), BillingWebhookEvent.received_at.asc())
                .with_for_update(skip_locked=True)
                .first()
            )
            if candidate is None:
                break
            updated = (
                db.query(BillingWebhookEvent)
                .filter(
                    BillingWebhookEvent.id == candidate.id,
                    or_(
                        (BillingWebhookEvent.processing_status == "pending")
                        & (BillingWebhookEvent.available_at <= now),
                        (BillingWebhookEvent.processing_status == "processing")
                        & (BillingWebhookEvent.claimed_at < stale_claim),
                    ),
                )
                .update(
                    {
                        BillingWebhookEvent.processing_status: "processing",
                        BillingWebhookEvent.claimed_at: now,
                        BillingWebhookEvent.attempt_count: BillingWebhookEvent.attempt_count + 1,
                    },
                    synchronize_session=False,
                )
            )
            if updated != 1:
                db.rollback()
                continue
            db.commit()
            event = db.get(BillingWebhookEvent, candidate.id)
            if event is None:
                continue
            try:
                _process_event(db, event)
                db.commit()
                processed += 1
            except (*_PROVIDER_ERRORS, SQLAlchemyError, BillingEventProcessingError) as exc:
                db.rollback()
                _fail_event(db, candidate.id, exc)
    return processed


def _sync_open_subscriptions(session_factory: Callable[[], Session] = SessionLocal) -> int:
    with session_factory() as db:
        subscription_ids = [
            subscription.razorpay_subscription_id
            for subscription in db.query(ClinicSubscription)
            .filter(
                ClinicSubscription.is_current.is_(True),
                ClinicSubscription.razorpay_subscription_id.is_not(None),
                ClinicSubscription.status.notin_(("cancelled", "completed", "expired", "creation_failed")),
            )
            .limit(500)
            .all()
            if subscription.razorpay_subscription_id is not None
        ]
    synced = 0
    for subscription_id in subscription_ids:
        with session_factory() as db:
            billing = (
                db.query(ClinicSubscription)
                .filter(
                    ClinicSubscription.razorpay_subscription_id == subscription_id,
                    ClinicSubscription.is_current.is_(True),
                )
                .with_for_update()
                .first()
            )
            if billing is None:
                continue
            try:
                provider_data = razorpay_service.fetch_subscription(subscription_id)
                _sync_subscription(db, billing, provider_data, "reconciliation")
                invoices = razorpay_service.fetch_subscription_invoices(subscription_id)
                for invoice_data in invoices.get("items", []):
                    _upsert_invoice(db, billing.clinic_id, subscription_id, invoice_data)
                db.commit()
                synced += 1
            except (*_PROVIDER_ERRORS, SQLAlchemyError, BillingEventProcessingError) as exc:
                db.rollback()
                logger.warning(
                    "Subscription reconciliation failed subscription_id=%s error_type=%s",
                    subscription_id,
                    type(exc).__name__,
                )
    return synced


def _suspend_expired_grace_periods(session_factory: Callable[[], Session] = SessionLocal) -> int:
    now = datetime.now(timezone.utc)
    suspended = 0
    with session_factory() as db:
        records = (
            db.query(ClinicSubscription)
            .filter(
                ClinicSubscription.is_current.is_(True),
                ClinicSubscription.status == "past_due",
                ClinicSubscription.grace_period_ends_at <= now,
                ClinicSubscription.last_synced_at
                >= now - timedelta(seconds=settings.subscription_reconciliation_interval_seconds * 2),
            )
            .with_for_update()
            .all()
        )
        for billing in records:
            clinic = db.get(Clinic, billing.clinic_id)
            if clinic is None:
                continue
            billing.status = "suspended"
            clinic.subscription_status = "suspended"
            db.add(
                AuditEvent(
                    clinic_id=clinic.id,
                    actor_type="system",
                    action="suspend",
                    resource_type="saas-subscription",
                    resource_id=billing.razorpay_subscription_id,
                    detail={"reason": "grace-period-expired"},
                )
            )
            suspended += 1
        db.commit()
    return suspended


def _run_dunning_cycle(session_factory: Callable[[], Session] = SessionLocal) -> int:
    """Process dunning for subscriptions with failed payments."""
    now = datetime.now(timezone.utc)
    dunning_count = 0
    with session_factory() as db:
        # Find subscriptions in past_due status that need dunning
        records = (
            db.query(ClinicSubscription)
            .filter(
                ClinicSubscription.is_current.is_(True),
                ClinicSubscription.status == "past_due",
                ClinicSubscription.payment_failure_count > 0,
                ClinicSubscription.payment_failure_count <= MAX_DUNNING_ATTEMPTS,
            )
            .with_for_update()
            .all()
        )
        for billing in records:
            clinic = db.get(Clinic, billing.clinic_id)
            if clinic is None:
                continue
            
            # Check if it's time for the next dunning attempt
            failure_count = billing.payment_failure_count
            if failure_count <= len(DUNNING_RETRY_DAYS):
                days_since_failure = (now - billing.last_synced_at).days if billing.last_synced_at else 0
                if days_since_failure >= DUNNING_RETRY_DAYS[failure_count - 1]:
                    # Trigger a payment retry by fetching the latest invoice
                    if billing.razorpay_subscription_id:
                        try:
                            invoices = razorpay_service.fetch_subscription_invoices(billing.razorpay_subscription_id)
                            latest_invoice = invoices.get("items", [])[0] if invoices.get("items") else None
                            if latest_invoice and latest_invoice.get("status") != "paid":
                                _send_dunning_email(db, clinic, billing, failure_count, latest_invoice)
                                dunning_count += 1
                        except (*_PROVIDER_ERRORS, SQLAlchemyError, BillingEventProcessingError) as exc:
                            logger.warning(
                                "Dunning cycle failed for subscription %s: %s",
                                billing.razorpay_subscription_id,
                                exc,
                            )
    return dunning_count


def run_worker() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting the subscription billing webhook worker.")
    last_reconciliation = 0.0
    last_dunning = 0.0
    while True:
        count = process_billing_webhook_batch()
        now = time.monotonic()
        if now - last_reconciliation >= settings.subscription_reconciliation_interval_seconds:
            _sync_open_subscriptions()
            last_reconciliation = now
        if now - last_dunning >= 86400:  # Run dunning once per day
            _run_dunning_cycle()
            last_dunning = now
        _suspend_expired_grace_periods()
        if count == 0:
            time.sleep(settings.billing_webhook_interval_seconds)


if __name__ == "__main__":
    run_worker()
