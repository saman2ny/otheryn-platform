import hashlib
import hmac
from uuid import uuid4

import razorpay
from razorpay.errors import SignatureVerificationError

from app.core.config import settings

_client: razorpay.Client | None = None


class RazorpayNotConfiguredError(RuntimeError):
    pass


def _get_client() -> razorpay.Client:
    global _client
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise RazorpayNotConfiguredError("RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are not set.")
    if _client is None:
        _client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
    return _client


def create_order(
    *,
    amount_subunits: int,
    currency: str,
    clinic_id: str,
    expires_at: int | None = None,
) -> dict:
    """amount_subunits is the amount in the smallest currency unit (e.g. cents/paise)."""
    client = _get_client()
    # Razorpay caps `receipt` at 40 chars — a full clinic UUID plus prefix/suffix would
    # overflow that, so use only its first 8 chars alongside a short random suffix.
    receipt = f"o_{clinic_id[:8]}_{uuid4().hex[:16]}"
    order_data = {
        "amount": amount_subunits,
        "currency": currency,
        "receipt": receipt,
        "payment_capture": 1,
    }
    if expires_at is not None:
        order_data["expire_by"] = expires_at
    return client.order.create(data=order_data)


def create_subscription(
    *,
    plan_id: str,
    total_count: int,
    clinic_id: str,
    plan_tier: str,
    billing_cycle: str,
) -> dict:
    return _get_client().subscription.create(
        data={
            "plan_id": plan_id,
            "total_count": total_count,
            "quantity": 1,
            "customer_notify": 1,
            "notes": {
                "clinic_id": clinic_id,
                "plan_tier": plan_tier,
                "billing_cycle": billing_cycle,
            },
        }
    )


def fetch_subscription(subscription_id: str) -> dict:
    return _get_client().subscription.fetch(subscription_id)


def cancel_subscription(subscription_id: str, *, cancel_at_cycle_end: bool) -> dict:
    return _get_client().subscription.cancel(
        subscription_id,
        {"cancel_at_cycle_end": cancel_at_cycle_end},
    )


def pause_subscription(subscription_id: str) -> dict:
    return _get_client().subscription.pause(subscription_id, {"pause_at": "now"})


def resume_subscription(subscription_id: str) -> dict:
    return _get_client().subscription.resume(subscription_id, {"resume_at": "now"})


def fetch_invoice(invoice_id: str) -> dict:
    return _get_client().invoice.fetch(invoice_id)


def fetch_subscription_invoices(subscription_id: str, *, count: int = 100) -> dict:
    return _get_client().invoice.all({"subscription_id": subscription_id, "count": count})


def verify_subscription_signature(
    *,
    razorpay_payment_id: str,
    razorpay_subscription_id: str,
    razorpay_signature: str,
) -> bool:
    if not settings.razorpay_key_secret:
        raise RazorpayNotConfiguredError("RAZORPAY_KEY_SECRET is not set.")
    message = f"{razorpay_payment_id}|{razorpay_subscription_id}".encode("utf-8")
    expected = hmac.new(settings.razorpay_key_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, razorpay_signature)


def fetch_payment(payment_id: str) -> dict:
    return _get_client().payment.fetch(payment_id)


def verify_signature(*, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    client = _get_client()
    try:
        return client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
    except SignatureVerificationError:
        return False
