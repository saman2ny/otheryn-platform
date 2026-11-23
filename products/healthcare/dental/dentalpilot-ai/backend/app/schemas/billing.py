from datetime import datetime
from typing import Literal

from app.schemas.common import CamelModel
from app.schemas.user import PlanTier

BillingCycle = Literal["monthly", "annual"]
SubscriptionStatus = Literal[
    "created",
    "authenticated",
    "active",
    "trialing",
    "past_due",
    "paused",
    "suspended",
    "canceled",
]
InvoiceStatus = Literal["paid", "open", "void"]


class SubscriptionPlan(CamelModel):
    tier: PlanTier
    name: str
    monthly_price: float
    annual_price: float
    ai_credits_per_month: int
    features: list[str]


class Subscription(CamelModel):
    plan_tier: PlanTier
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    current_period_end: datetime
    grace_period_ends_at: datetime | None = None
    cancel_at_cycle_end: bool = False
    payment_failure_count: int = 0
    razorpay_subscription_id: str | None = None
    ai_credits_used: int
    ai_credits_limit: int


class Invoice(CamelModel):
    id: str
    amount: float
    currency: str
    issued_at: datetime
    status: InvoiceStatus
    download_url: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None


class CreateOrderRequest(CamelModel):
    plan_tier: PlanTier
    billing_cycle: BillingCycle


class CreateOrderResponse(CamelModel):
    requires_payment: bool
    # Populated when requires_payment is true (paid plan — open the Razorpay modal):
    order_id: str | None = None
    amount: int | None = None  # smallest currency unit (e.g. cents)
    currency: str | None = None
    key_id: str | None = None
    # Populated when requires_payment is false (free plan — already applied, no payment needed):
    subscription: Subscription | None = None


class VerifyPaymentRequest(CamelModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class SubscriptionCheckoutRequest(CamelModel):
    plan_tier: PlanTier
    billing_cycle: BillingCycle


class SubscriptionCheckoutResponse(CamelModel):
    requires_payment: bool
    subscription: Subscription | None = None
    razorpay_subscription_id: str | None = None
    key_id: str | None = None
    short_url: str | None = None


class VerifySubscriptionRequest(CamelModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


class SubscriptionCancellationRequest(CamelModel):
    cancel_at_cycle_end: bool = True


class TreatmentPaymentOrderCreate(CamelModel):
    charge_entry_id: str


class TreatmentPaymentOrderResponse(CamelModel):
    order_id: str
    amount: int
    currency: str
    key_id: str
    charge_entry_id: str
    balance_amount: float
    status: str


class PatientPortalTreatmentCharge(CamelModel):
    charge_entry_id: str
    amount: float
    paid_amount: float
    balance_amount: float
    currency: str
    payment_enabled: bool


class TreatmentPaymentVerifyResponse(CamelModel):
    payment_id: str
    ledger_entry_id: str
    charge_entry_id: str
    amount: float
    currency: str
    status: str
