from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func

from app.core.deps import CurrentUser, DbSession
from app.models.billing import Invoice
from app.models.clinic import Clinic
from app.models.healthcare import (
    ClinicBranch,
    InsuranceClaim,
    Patient,
    PatientEnquiry,
    PatientVisit,
    RecallReminder,
    TreatmentLedgerEntry,
    TreatmentPlan,
    TreatmentStage,
)
from app.models.user import User
from app.schemas.dashboard import (
    ClinicOperationalMetrics,
    FinancialSummary,
    FollowupTypeMetrics,
    InsuranceClaimsSummary,
    MonthlyRevenuePoint,
    PatientRetentionMetrics,
    RevenueMetrics,
    TreatmentFollowupMetrics,
)

router = APIRouter(prefix="/analytics", tags=["financial-analytics"])


def _utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _validate_date_range(from_date: datetime | None, to_date: datetime | None) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    window_end = _utc_datetime(to_date) if to_date else now
    window_start = _utc_datetime(from_date) if from_date else window_end - timedelta(days=30)
    if window_start >= window_end or (window_end - window_start).days > 366:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Choose a valid analytics range of at most 366 days.",
        )
    return window_start, window_end


def _get_clinic_currency(db: DbSession, clinic_id: str) -> str:
    currency_row = (
        db.query(TreatmentLedgerEntry.currency)
        .filter(TreatmentLedgerEntry.clinic_id == clinic_id)
        .first()
    )
    if currency_row:
        return currency_row[0]
    plan_row = (
        db.query(TreatmentPlan.currency)
        .filter(TreatmentPlan.clinic_id == clinic_id)
        .first()
    )
    if plan_row:
        return plan_row[0]
    return "INR"


@router.get("/revenue", response_model=RevenueMetrics)
def get_revenue_metrics(
    current_user: CurrentUser,
    db: DbSession,
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
) -> RevenueMetrics:
    window_start, window_end = _validate_date_range(from_date, to_date)
    currency = _get_clinic_currency(db, current_user.clinic_id)

    ledger_query = db.query(TreatmentLedgerEntry).filter(
        TreatmentLedgerEntry.clinic_id == current_user.clinic_id,
        TreatmentLedgerEntry.created_at >= window_start,
        TreatmentLedgerEntry.created_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        ledger_query = ledger_query.filter(TreatmentLedgerEntry.branch_id == current_user.branch_id)

    ledger_entries = ledger_query.all()

    charges = [e for e in ledger_entries if e.entry_type == "charge"]
    payments = [e for e in ledger_entries if e.entry_type == "payment"]
    refunds = [e for e in ledger_entries if e.entry_type == "refund"]

    treatment_revenue = sum(float(e.amount) for e in charges)
    patient_payments_collected = sum(float(e.amount) for e in payments if e.method != "insurance")
    insurance_payments_collected = sum(float(e.amount) for e in payments if e.method == "insurance")
    refunds_issued = sum(float(e.amount) for e in refunds)
    net_revenue = patient_payments_collected + insurance_payments_collected - refunds_issued

    charges_by_category: dict[str, float] = {}
    for e in charges:
        charges_by_category[e.method] = charges_by_category.get(e.method, 0) + float(e.amount)

    payments_by_method: dict[str, float] = {}
    for e in payments:
        payments_by_method[e.method] = payments_by_method.get(e.method, 0) + float(e.amount)

    outstanding_query = db.query(TreatmentLedgerEntry).filter(
        TreatmentLedgerEntry.clinic_id == current_user.clinic_id,
        TreatmentLedgerEntry.entry_type == "charge",
    )
    if current_user.role == "staff" and current_user.branch_id:
        outstanding_query = outstanding_query.filter(TreatmentLedgerEntry.branch_id == current_user.branch_id)

    outstanding_charges = outstanding_query.all()
    outstanding_receivables = 0.0
    for charge in outstanding_charges:
        related_payments = sum(
            float(e.amount) for e in outstanding_charges
            if e.charge_entry_id == charge.id and e.entry_type == "payment"
        )
        related_refunds = sum(
            float(e.amount) for e in outstanding_charges
            if e.charge_entry_id == charge.id and e.entry_type == "refund"
        )
        outstanding_receivables += float(charge.amount) - related_payments + related_refunds

    subscription_query = db.query(Invoice).filter(
        Invoice.clinic_id == current_user.clinic_id,
        Invoice.issued_at >= window_start,
        Invoice.issued_at < window_end,
        Invoice.status == "paid",
    )
    subscription_revenue = sum(float(inv.amount) for inv in subscription_query.all())

    monthly_trend: list[MonthlyRevenuePoint] = []
    current_month = window_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while current_month < window_end:
        next_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_start = current_month
        month_end = min(next_month, window_end)

        month_ledger = db.query(TreatmentLedgerEntry).filter(
            TreatmentLedgerEntry.clinic_id == current_user.clinic_id,
            TreatmentLedgerEntry.created_at >= month_start,
            TreatmentLedgerEntry.created_at < month_end,
        )
        if current_user.role == "staff" and current_user.branch_id:
            month_ledger = month_ledger.filter(TreatmentLedgerEntry.branch_id == current_user.branch_id)

        month_entries = month_ledger.all()
        month_charges = [e for e in month_entries if e.entry_type == "charge"]
        month_payments = [e for e in month_entries if e.entry_type == "payment"]
        month_insurance = [e for e in month_payments if e.method == "insurance"]
        month_patient = [e for e in month_payments if e.method != "insurance"]

        monthly_trend.append(MonthlyRevenuePoint(
            month=current_month.strftime("%Y-%m"),
            revenue=sum(float(e.amount) for e in month_payments),
            treatment_revenue=sum(float(e.amount) for e in month_charges),
            subscription_revenue=0.0,
            patient_payments=sum(float(e.amount) for e in month_patient),
            insurance_payments=sum(float(e.amount) for e in month_insurance),
        ))
        current_month = next_month

    revenue_by_category = {
        "treatment_charges": treatment_revenue,
        "subscription_revenue": subscription_revenue,
    }

    return RevenueMetrics(
        period_start=window_start,
        period_end=window_end,
        currency=currency,
        total_revenue=treatment_revenue + subscription_revenue,
        treatment_revenue=treatment_revenue,
        subscription_revenue=subscription_revenue,
        patient_payments_collected=patient_payments_collected,
        insurance_payments_collected=insurance_payments_collected,
        refunds_issued=refunds_issued,
        net_revenue=net_revenue,
        outstanding_receivables=max(outstanding_receivables, 0),
        revenue_by_category=revenue_by_category,
        revenue_by_payment_method=payments_by_method,
        monthly_trend=monthly_trend,
    )


@router.get("/financial-summary", response_model=FinancialSummary)
def get_financial_summary(
    current_user: CurrentUser,
    db: DbSession,
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
) -> FinancialSummary:
    window_start, window_end = _validate_date_range(from_date, to_date)
    currency = _get_clinic_currency(db, current_user.clinic_id)

    clinic = db.get(Clinic, current_user.clinic_id)
    clinic_name = clinic.name if clinic else "Unknown Clinic"

    ledger_query = db.query(TreatmentLedgerEntry).filter(
        TreatmentLedgerEntry.clinic_id == current_user.clinic_id,
        TreatmentLedgerEntry.created_at >= window_start,
        TreatmentLedgerEntry.created_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        ledger_query = ledger_query.filter(TreatmentLedgerEntry.branch_id == current_user.branch_id)

    ledger_entries = ledger_query.all()

    charges = [e for e in ledger_entries if e.entry_type == "charge"]
    payments = [e for e in ledger_entries if e.entry_type == "payment"]
    refunds = [e for e in ledger_entries if e.entry_type == "refund"]

    total_charges = sum(float(e.amount) for e in charges)
    total_payments = sum(float(e.amount) for e in payments)
    total_refunds = sum(float(e.amount) for e in refunds)
    net_collected = total_payments - total_refunds

    charges_by_type: dict[str, float] = {}
    for e in charges:
        charges_by_type[e.method] = charges_by_type.get(e.method, 0) + float(e.amount)

    payments_by_method: dict[str, float] = {}
    for e in payments:
        payments_by_method[e.method] = payments_by_method.get(e.method, 0) + float(e.amount)

    outstanding_query = db.query(TreatmentLedgerEntry).filter(
        TreatmentLedgerEntry.clinic_id == current_user.clinic_id,
        TreatmentLedgerEntry.entry_type == "charge",
    )
    if current_user.role == "staff" and current_user.branch_id:
        outstanding_query = outstanding_query.filter(TreatmentLedgerEntry.branch_id == current_user.branch_id)

    outstanding_charges = outstanding_query.all()
    outstanding_balance = 0.0
    for charge in outstanding_charges:
        related_payments = sum(
            float(e.amount) for e in outstanding_charges
            if e.charge_entry_id == charge.id and e.entry_type == "payment"
        )
        related_refunds = sum(
            float(e.amount) for e in outstanding_charges
            if e.charge_entry_id == charge.id and e.entry_type == "refund"
        )
        outstanding_balance += float(charge.amount) - related_payments + related_refunds

    claims_query = db.query(InsuranceClaim).filter(
        InsuranceClaim.clinic_id == current_user.clinic_id,
        InsuranceClaim.created_at >= window_start,
        InsuranceClaim.created_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        claims_query = claims_query.filter(InsuranceClaim.branch_id == current_user.branch_id)

    claims = claims_query.all()
    total_claims = len(claims)
    total_billed = sum(float(c.billed_amount) for c in claims)
    total_approved = sum(float(c.approved_amount or 0) for c in claims)
    total_paid = sum(float(c.paid_amount) for c in claims)
    pending_claims = sum(1 for c in claims if c.status in ("submitted", "in-review", "draft"))
    denied_claims = sum(1 for c in claims if c.status == "denied")
    approval_rate = (total_approved / total_billed * 100) if total_billed > 0 else 0
    collection_rate = (total_paid / total_approved * 100) if total_approved > 0 else 0

    return FinancialSummary(
        clinic_id=current_user.clinic_id,
        clinic_name=clinic_name,
        currency=currency,
        period_start=window_start,
        period_end=window_end,
        total_charges=total_charges,
        total_payments=total_payments,
        total_refunds=total_refunds,
        net_collected=net_collected,
        outstanding_balance=max(outstanding_balance, 0),
        charges_by_type=charges_by_type,
        payments_by_method=payments_by_method,
        insurance_claims=InsuranceClaimsSummary(
            total_claims=total_claims,
            total_billed=total_billed,
            total_approved=total_approved,
            total_paid=total_paid,
            pending_claims=pending_claims,
            denied_claims=denied_claims,
            approval_rate=approval_rate,
            collection_rate=collection_rate,
        ),
    )


@router.get("/treatment-followup", response_model=TreatmentFollowupMetrics)
def get_treatment_followup_metrics(
    current_user: CurrentUser,
    db: DbSession,
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
) -> TreatmentFollowupMetrics:
    window_start, window_end = _validate_date_range(from_date, to_date)

    stages_query = (
        db.query(TreatmentStage)
        .join(TreatmentPlan, TreatmentPlan.id == TreatmentStage.plan_id)
        .join(Patient, Patient.id == TreatmentPlan.patient_id)
        .filter(TreatmentStage.clinic_id == current_user.clinic_id)
    )
    if current_user.role == "staff" and current_user.branch_id:
        stages_query = stages_query.filter(Patient.branch_id == current_user.branch_id)

    stages_query = stages_query.filter(
        TreatmentStage.created_at >= window_start,
        TreatmentStage.created_at < window_end,
    )
    stages = stages_query.all()

    total_stages = len(stages)
    completed_stages = sum(1 for s in stages if s.status == "completed")
    deferred_stages = sum(1 for s in stages if s.status == "deferred")
    declined_stages = sum(1 for s in stages if s.status == "declined")
    pending_stages = sum(1 for s in stages if s.status in ("recommended", "accepted", "scheduled"))
    overdue_stages = sum(
        1 for s in stages
        if s.status in ("recommended", "accepted", "scheduled")
        and s.scheduled_at is not None
        and _utc_datetime(s.scheduled_at) < datetime.now(timezone.utc)
    )

    conversion_rate = (
        sum(1 for s in stages if s.status in ("accepted", "scheduled", "completed")) / total_stages * 100
        if total_stages else 0
    )
    completion_rate = (completed_stages / total_stages * 100) if total_stages else 0

    reminders_query = db.query(RecallReminder).join(
        Patient, Patient.id == RecallReminder.patient_id
    ).filter(
        RecallReminder.clinic_id == current_user.clinic_id,
        RecallReminder.created_at >= window_start,
        RecallReminder.created_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        reminders_query = reminders_query.filter(Patient.branch_id == current_user.branch_id)

    reminders = reminders_query.all()
    followup_sent = len(reminders)
    followup_completed = sum(1 for r in reminders if r.status == "completed")
    followup_completion_rate = (followup_completed / followup_sent * 100) if followup_sent else 0

    followup_by_type: dict[str, FollowupTypeMetrics] = {}
    for reminder in reminders:
        if reminder.reminder_type not in followup_by_type:
            followup_by_type[reminder.reminder_type] = FollowupTypeMetrics(sent=0, completed=0, completion_rate=0)
        followup_by_type[reminder.reminder_type].sent += 1
        if reminder.status == "completed":
            followup_by_type[reminder.reminder_type].completed += 1

    for metrics in followup_by_type.values():
        metrics.completion_rate = (metrics.completed / metrics.sent * 100) if metrics.sent else 0

    completed_stages_list = [s for s in stages if s.status == "completed" and s.completed_at and s.created_at]
    avg_days_to_completion = None
    if completed_stages_list:
        total_days = sum(
            (_utc_datetime(s.completed_at) - _utc_datetime(s.created_at)).days
            for s in completed_stages_list
        )
        avg_days_to_completion = total_days / len(completed_stages_list)

    return TreatmentFollowupMetrics(
        period_start=window_start,
        period_end=window_end,
        total_stages=total_stages,
        completed_stages=completed_stages,
        deferred_stages=deferred_stages,
        declined_stages=declined_stages,
        pending_stages=pending_stages,
        overdue_stages=overdue_stages,
        completion_rate=completion_rate,
        conversion_rate=conversion_rate,
        followup_sent=followup_sent,
        followup_completed=followup_completed,
        followup_completion_rate=followup_completion_rate,
        avg_days_to_completion=avg_days_to_completion,
        followup_by_type=followup_by_type,
    )


@router.get("/patient-retention", response_model=PatientRetentionMetrics)
def get_patient_retention_metrics(
    current_user: CurrentUser,
    db: DbSession,
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
) -> PatientRetentionMetrics:
    window_start, window_end = _validate_date_range(from_date, to_date)

    visits_query = db.query(PatientVisit).join(
        Patient, Patient.id == PatientVisit.patient_id
    ).filter(
        PatientVisit.clinic_id == current_user.clinic_id,
        PatientVisit.status == "completed",
        PatientVisit.completed_at >= window_start,
        PatientVisit.completed_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        visits_query = visits_query.filter(PatientVisit.branch_id == current_user.branch_id)

    completed_visits = visits_query.all()
    patient_visit_counts: dict[str, int] = {}
    for visit in completed_visits:
        patient_visit_counts[visit.patient_id] = patient_visit_counts.get(visit.patient_id, 0) + 1

    unique_patients_seen = len(patient_visit_counts)
    returning_patients = sum(1 for count in patient_visit_counts.values() if count > 1)
    retention_rate = (returning_patients / unique_patients_seen * 100) if unique_patients_seen else 0
    avg_visits_per_patient = (
        sum(patient_visit_counts.values()) / unique_patients_seen if unique_patients_seen else 0
    )

    new_patients_query = db.query(Patient).filter(
        Patient.clinic_id == current_user.clinic_id,
        Patient.created_at >= window_start,
        Patient.created_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        new_patients_query = new_patients_query.filter(Patient.branch_id == current_user.branch_id)
    new_patients = new_patients_query.count()

    treatment_completed = db.query(TreatmentStage).join(
        TreatmentPlan, TreatmentPlan.id == TreatmentStage.plan_id
    ).join(Patient, Patient.id == TreatmentPlan.patient_id).filter(
        TreatmentStage.clinic_id == current_user.clinic_id,
        TreatmentStage.status == "completed",
        TreatmentStage.completed_at >= window_start,
        TreatmentStage.completed_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        treatment_completed = treatment_completed.filter(Patient.branch_id == current_user.branch_id)

    patients_with_completed_treatment = treatment_completed.distinct(Patient.id).count()
    treatment_completion_rate = (
        patients_with_completed_treatment / unique_patients_seen * 100 if unique_patients_seen else 0
    )

    return PatientRetentionMetrics(
        period_start=window_start,
        period_end=window_end,
        new_patients=new_patients,
        returning_patients=returning_patients,
        total_unique_patients=unique_patients_seen,
        retention_rate=retention_rate,
        avg_visits_per_patient=avg_visits_per_patient,
        patients_with_completed_treatment=patients_with_completed_treatment,
        treatment_completion_rate=treatment_completion_rate,
    )


@router.get("/operational", response_model=ClinicOperationalMetrics)
def get_operational_metrics(
    current_user: CurrentUser,
    db: DbSession,
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
) -> ClinicOperationalMetrics:
    window_start, window_end = _validate_date_range(from_date, to_date)

    visits_query = db.query(PatientVisit).join(
        Patient, Patient.id == PatientVisit.patient_id
    ).filter(
        PatientVisit.clinic_id == current_user.clinic_id,
        PatientVisit.created_at >= window_start,
        PatientVisit.created_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        visits_query = visits_query.filter(PatientVisit.branch_id == current_user.branch_id)

    all_visits = visits_query.all()
    total_visits = len(all_visits)
    completed_visits = sum(1 for v in all_visits if v.status == "completed")
    cancelled_visits = sum(1 for v in all_visits if v.status == "cancelled")
    no_show_visits = sum(1 for v in all_visits if v.status == "no-show")
    scheduled_visits = sum(1 for v in all_visits if v.status == "scheduled")
    no_show_rate = (no_show_visits / total_visits * 100) if total_visits else 0

    enquiries_query = db.query(PatientEnquiry).filter(
        PatientEnquiry.clinic_id == current_user.clinic_id,
        PatientEnquiry.created_at >= window_start,
        PatientEnquiry.created_at < window_end,
    )
    if current_user.role == "staff" and current_user.branch_id:
        enquiries_query = enquiries_query.filter(PatientEnquiry.branch_id == current_user.branch_id)

    all_enquiries = enquiries_query.all()
    total_enquiries = len(all_enquiries)
    converted_enquiries = sum(1 for e in all_enquiries if e.status == "converted")
    enquiry_conversion_rate = (converted_enquiries / total_enquiries * 100) if total_enquiries else 0

    branch_query = db.query(ClinicBranch).filter(ClinicBranch.clinic_id == current_user.clinic_id)
    if current_user.role == "staff" and current_user.branch_id:
        branch_query = branch_query.filter(ClinicBranch.id == current_user.branch_id)
    branch_count = branch_query.count()

    staff_count = db.query(User).filter(
        User.clinic_id == current_user.clinic_id,
    ).count()

    return ClinicOperationalMetrics(
        period_start=window_start,
        period_end=window_end,
        total_visits=total_visits,
        completed_visits=completed_visits,
        cancelled_visits=cancelled_visits,
        no_show_visits=no_show_visits,
        no_show_rate=no_show_rate,
        scheduled_visits=scheduled_visits,
        total_enquiries=total_enquiries,
        converted_enquiries=converted_enquiries,
        enquiry_conversion_rate=enquiry_conversion_rate,
        avg_wait_time_days=None,
        branch_count=branch_count,
        active_staff_count=staff_count,
    )