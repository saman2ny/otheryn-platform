from datetime import datetime
from decimal import Decimal
from typing import Literal

from app.schemas.common import CamelModel
from app.schemas.user import PlanTier


class DashboardContentItem(CamelModel):
    id: str
    headline: str
    platform: str
    created_at: datetime


class DashboardEventItem(CamelModel):
    id: str
    title: str
    platform: str
    scheduled_at: datetime


class DashboardSummary(CamelModel):
    content_generated_this_month: int
    posts_scheduled_upcoming: int
    ai_credits_used: int
    ai_credits_limit: int
    plan_tier: PlanTier
    recent_content: list[DashboardContentItem]
    upcoming_events: list[DashboardEventItem]


class RevenueMetrics(CamelModel):
    period_start: datetime
    period_end: datetime
    currency: str
    total_revenue: float
    treatment_revenue: float
    subscription_revenue: float
    patient_payments_collected: float
    insurance_payments_collected: float
    refunds_issued: float
    net_revenue: float
    outstanding_receivables: float
    revenue_by_category: dict[str, float]
    revenue_by_payment_method: dict[str, float]
    monthly_trend: list[MonthlyRevenuePoint]


class MonthlyRevenuePoint(CamelModel):
    month: str
    revenue: float
    treatment_revenue: float
    subscription_revenue: float
    patient_payments: float
    insurance_payments: float


class FinancialSummary(CamelModel):
    clinic_id: str
    clinic_name: str
    currency: str
    period_start: datetime
    period_end: datetime
    total_charges: float
    total_payments: float
    total_refunds: float
    net_collected: float
    outstanding_balance: float
    charges_by_type: dict[str, float]
    payments_by_method: dict[str, float]
    insurance_claims: InsuranceClaimsSummary


class InsuranceClaimsSummary(CamelModel):
    total_claims: int
    total_billed: float
    total_approved: float
    total_paid: float
    pending_claims: int
    denied_claims: int
    approval_rate: float
    collection_rate: float


class TreatmentFollowupMetrics(CamelModel):
    period_start: datetime
    period_end: datetime
    total_stages: int
    completed_stages: int
    deferred_stages: int
    declined_stages: int
    pending_stages: int
    overdue_stages: int
    completion_rate: float
    conversion_rate: float
    followup_sent: int
    followup_completed: int
    followup_completion_rate: float
    avg_days_to_completion: float | None = None
    followup_by_type: dict[str, FollowupTypeMetrics]


class FollowupTypeMetrics(CamelModel):
    sent: int
    completed: int
    completion_rate: float


class PatientRetentionMetrics(CamelModel):
    period_start: datetime
    period_end: datetime
    new_patients: int
    returning_patients: int
    total_unique_patients: int
    retention_rate: float
    avg_visits_per_patient: float
    patients_with_completed_treatment: int
    treatment_completion_rate: float


class ClinicOperationalMetrics(CamelModel):
    period_start: datetime
    period_end: datetime
    total_visits: int
    completed_visits: int
    cancelled_visits: int
    no_show_visits: int
    no_show_rate: float
    scheduled_visits: int
    total_enquiries: int
    converted_enquiries: int
    enquiry_conversion_rate: float
    avg_wait_time_days: float | None = None
    branch_count: int
    active_staff_count: int
