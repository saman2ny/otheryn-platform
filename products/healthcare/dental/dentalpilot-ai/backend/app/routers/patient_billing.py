import csv
import hashlib
import hmac
import io
import json
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from razorpay.errors import BadRequestError, GatewayError, ServerError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentPatient, CurrentUser, DbSession
from app.models.billing import PatientPaymentOrder
from app.models.healthcare import AuditEvent, Patient, PatientPortalAccount, TreatmentLedgerEntry
from app.schemas.billing import (
    TreatmentPaymentOrderCreate,
    TreatmentPaymentOrderResponse,
    TreatmentPaymentVerifyResponse,
    PatientPortalTreatmentCharge,
    VerifyPaymentRequest,
)
from app.services import razorpay_service
from app.services.integration_adapters import IntegrationContext, REGISTRY
from app.services.patient_payments import PAYMENT_ORDER_TTL
from app.services.razorpay_service import RazorpayNotConfiguredError

router = APIRouter(prefix="/billing", tags=["patient-billing"])
MAX_RECONCILIATION_FILE_BYTES = 5_000_000
MAX_RECONCILIATION_ROWS = 10_000
RECONCILIATION_FIELDS = {
    "transactionReference",
    "patientReference",
    "entryType",
    "amount",
    "currency",
}


def _spreadsheet_safe(value: object) -> object:
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _require_staff(current_user: CurrentUser) -> None:
    if current_user.role not in ("owner", "staff"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinic staff access is required.")


def _charge_balance(db: Session, charge: TreatmentLedgerEntry) -> Decimal:
    related_entries = (
        db.query(TreatmentLedgerEntry)
        .filter(
            TreatmentLedgerEntry.clinic_id == charge.clinic_id,
            TreatmentLedgerEntry.charge_entry_id == charge.id,
        )
        .all()
    )
    payments = sum(
        (entry.amount for entry in related_entries if entry.entry_type == "payment"),
        Decimal("0"),
    )
    refunds = sum(
        (entry.amount for entry in related_entries if entry.entry_type == "refund"),
        Decimal("0"),
    )
    return charge.amount - payments + refunds


def _charge_for_user(
    db: Session,
    current_user: CurrentUser,
    charge_entry_id: str,
    *,
    lock: bool = False,
) -> TreatmentLedgerEntry:
    query = db.query(TreatmentLedgerEntry).filter(
        TreatmentLedgerEntry.id == charge_entry_id,
        TreatmentLedgerEntry.clinic_id == current_user.clinic_id,
        TreatmentLedgerEntry.entry_type == "charge",
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(TreatmentLedgerEntry.branch_id == current_user.branch_id)
    if lock:
        query = query.with_for_update()
    charge = query.first()
    if charge is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treatment charge not found.")
    return charge


def _patient_payment_response(
    order: PatientPaymentOrder, *, balance_amount: Decimal | None = None
) -> TreatmentPaymentOrderResponse:
    if not settings.razorpay_key_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Razorpay is not configured. Set RAZORPAY_KEY_ID on the backend.",
        )
    return TreatmentPaymentOrderResponse(
        order_id=order.razorpay_order_id,
        amount=order.amount_subunits,
        currency=order.currency,
        key_id=settings.razorpay_key_id,
        charge_entry_id=order.charge_entry_id,
        balance_amount=float(balance_amount if balance_amount is not None else order.amount),
        status=order.status,
    )


def _create_payment_order_for_charge(
    db: Session,
    charge: TreatmentLedgerEntry,
    *,
    actor_id: str,
    actor_type: str,
    initiated_by_patient: bool,
) -> TreatmentPaymentOrderResponse:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Patient payments are not configured. Set Razorpay credentials on the backend.",
        )
    if charge.currency != settings.patient_payment_currency.upper():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Treatment charge currency must match PATIENT_PAYMENT_CURRENCY.",
        )
    outstanding = _charge_balance(db, charge)
    if outstanding <= 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "This treatment charge has no balance due.")

    now = datetime.now(timezone.utc)
    existing_order = (
        db.query(PatientPaymentOrder)
        .filter(
            PatientPaymentOrder.charge_entry_id == charge.id,
            PatientPaymentOrder.status == "created",
        )
        .with_for_update()
        .first()
    )
    if existing_order is not None:
        created_at = existing_order.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at + PAYMENT_ORDER_TTL > now and existing_order.amount == outstanding:
            return _patient_payment_response(existing_order, balance_amount=outstanding)
        existing_order.status = "expired"
        db.flush()

    amount_subunits = int(outstanding * 100)
    if Decimal(amount_subunits) / Decimal(100) != outstanding:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Razorpay supports two-decimal payment amounts only.",
        )
    try:
        provider_order = razorpay_service.create_order(
            amount_subunits=amount_subunits,
            currency=charge.currency,
            clinic_id=charge.clinic_id,
            expires_at=int((now + PAYMENT_ORDER_TTL).timestamp()),
        )
    except RazorpayNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Razorpay is not configured.") from exc
    except (BadRequestError, GatewayError, ServerError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Razorpay could not create the payment order.") from exc

    if provider_order.get("amount") != amount_subunits or provider_order.get("currency") != charge.currency:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Razorpay returned an order with an unexpected amount or currency.",
        )
    order = PatientPaymentOrder(
        clinic_id=charge.clinic_id,
        branch_id=charge.branch_id,
        patient_id=charge.patient_id,
        charge_entry_id=charge.id,
        razorpay_order_id=provider_order["id"],
        amount=outstanding,
        amount_subunits=amount_subunits,
        currency=charge.currency,
        created_by=actor_id,
        initiated_by_patient=initiated_by_patient,
    )
    db.add(order)
    db.add(
        AuditEvent(
            clinic_id=charge.clinic_id,
            branch_id=charge.branch_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action="create-payment-order",
            resource_type="treatment-charge",
            resource_id=charge.id,
            detail={"amount": str(outstanding), "currency": charge.currency},
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing_order = (
            db.query(PatientPaymentOrder)
            .filter(
                PatientPaymentOrder.charge_entry_id == charge.id,
                PatientPaymentOrder.status == "created",
            )
            .first()
        )
        if existing_order is not None:
            return _patient_payment_response(existing_order, balance_amount=outstanding)
        raise HTTPException(status.HTTP_409_CONFLICT, "A payment order could not be created.") from exc
    db.refresh(order)
    return _patient_payment_response(order, balance_amount=outstanding)


def _record_captured_payment(
    db: Session,
    order: PatientPaymentOrder,
    *,
    payment_id: str,
    amount_subunits: int,
    currency: str,
) -> TreatmentPaymentVerifyResponse:
    if order.status == "paid":
        if order.razorpay_payment_id != payment_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "This order was already settled by a different payment.",
            )
        if order.payment_ledger_entry_id is None:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "The settled payment is missing its ledger entry.",
            )
        return TreatmentPaymentVerifyResponse(
            payment_id=payment_id,
            ledger_entry_id=order.payment_ledger_entry_id,
            charge_entry_id=order.charge_entry_id,
            amount=float(order.amount),
            currency=order.currency,
            status="paid",
        )
    if order.status != "created":
        raise HTTPException(status.HTTP_409_CONFLICT, "This payment order is no longer active.")
    if amount_subunits != order.amount_subunits or currency.upper() != order.currency:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The captured payment amount or currency does not match the clinic order.",
        )
    duplicate_payment = (
        db.query(PatientPaymentOrder.id)
        .filter(PatientPaymentOrder.razorpay_payment_id == payment_id)
        .first()
    )
    if duplicate_payment is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This Razorpay payment was already recorded.")

    charge = db.get(TreatmentLedgerEntry, order.charge_entry_id)
    if charge is None or charge.clinic_id != order.clinic_id or charge.patient_id != order.patient_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "The original treatment charge is unavailable.")
    payment_entry = TreatmentLedgerEntry(
        clinic_id=order.clinic_id,
        branch_id=order.branch_id,
        patient_id=order.patient_id,
        stage_id=charge.stage_id,
        charge_entry_id=charge.id,
        entry_type="payment",
        amount=order.amount,
        currency=order.currency,
        method="razorpay",
        reference=payment_id,
        notes=f"Razorpay order {order.razorpay_order_id}",
        actor_id=order.created_by,
    )
    db.add(payment_entry)
    db.flush()
    order.razorpay_payment_id = payment_id
    order.payment_ledger_entry_id = payment_entry.id
    order.status = "paid"
    order.paid_at = datetime.now(timezone.utc)
    db.add(
        AuditEvent(
            clinic_id=order.clinic_id,
            branch_id=order.branch_id,
            actor_id=order.created_by,
            actor_type="patient" if order.initiated_by_patient else "system",
            action="payment-captured",
            resource_type="treatment-ledger-entry",
            resource_id=payment_entry.id,
            detail={
                "paymentOrderId": order.id,
                "razorpayPaymentId": payment_id,
                "amount": str(order.amount),
                "currency": order.currency,
            },
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This payment was already recorded.") from exc
    db.refresh(order)
    return TreatmentPaymentVerifyResponse(
        payment_id=payment_id,
        ledger_entry_id=payment_entry.id,
        charge_entry_id=order.charge_entry_id,
        amount=float(order.amount),
        currency=order.currency,
        status="paid",
    )


def _verify_payment_order(
    db: Session,
    order: PatientPaymentOrder,
    request: VerifyPaymentRequest,
) -> TreatmentPaymentVerifyResponse:
    if order.status == "paid":
        return _record_captured_payment(
            db,
            order,
            payment_id=request.razorpay_payment_id,
            amount_subunits=order.amount_subunits,
            currency=order.currency,
        )
    if order.status != "created":
        raise HTTPException(status.HTTP_409_CONFLICT, "This payment order is no longer active.")

    try:
        signature_valid = razorpay_service.verify_signature(
            razorpay_order_id=request.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature,
        )
        if not signature_valid:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment verification failed.")
        payment = razorpay_service.fetch_payment(request.razorpay_payment_id)
    except RazorpayNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Razorpay is not configured.") from exc
    except (BadRequestError, GatewayError, ServerError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Unable to verify Razorpay payment status.") from exc
    if (
        payment.get("order_id") != order.razorpay_order_id
        or payment.get("status") != "captured"
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Razorpay has not captured this payment yet.")
    return _record_captured_payment(
        db,
        order,
        payment_id=request.razorpay_payment_id,
        amount_subunits=payment.get("amount", 0),
        currency=payment.get("currency", ""),
    )


@router.post(
    "/treatment-payments/order",
    response_model=TreatmentPaymentOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_treatment_payment_order(
    request: TreatmentPaymentOrderCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> TreatmentPaymentOrderResponse:
    _require_staff(current_user)
    charge = _charge_for_user(db, current_user, request.charge_entry_id, lock=True)
    return _create_payment_order_for_charge(
        db,
        charge,
        actor_id=current_user.id,
        actor_type=current_user.role,
        initiated_by_patient=False,
    )


@router.post(
    "/treatment-payments/verify",
    response_model=TreatmentPaymentVerifyResponse,
)
def verify_treatment_payment(
    request: VerifyPaymentRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> TreatmentPaymentVerifyResponse:
    _require_staff(current_user)
    query = db.query(PatientPaymentOrder).filter(
        PatientPaymentOrder.razorpay_order_id == request.razorpay_order_id,
        PatientPaymentOrder.clinic_id == current_user.clinic_id,
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(PatientPaymentOrder.branch_id == current_user.branch_id)
    order = query.with_for_update().first()
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treatment payment order not found.")
    return _verify_payment_order(db, order, request)


def _patient_for_payment_account(db: Session, account: PatientPortalAccount) -> Patient:
    patient = (
        db.query(Patient)
        .filter(
            Patient.id == account.patient_id,
            Patient.clinic_id == account.clinic_id,
        )
        .first()
    )
    if patient is None or not patient.email or patient.email.lower() != account.email.lower():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Patient portal account is no longer valid.")
    return patient


@router.get(
    "/treatment-payments/portal/charges",
    response_model=list[PatientPortalTreatmentCharge],
)
def list_patient_portal_charges(
    account: CurrentPatient,
    db: DbSession,
) -> list[PatientPortalTreatmentCharge]:
    patient = _patient_for_payment_account(db, account)
    charges = (
        db.query(TreatmentLedgerEntry)
        .filter(
            TreatmentLedgerEntry.clinic_id == patient.clinic_id,
            TreatmentLedgerEntry.patient_id == patient.id,
            TreatmentLedgerEntry.entry_type == "charge",
        )
        .order_by(TreatmentLedgerEntry.created_at.desc())
        .all()
    )
    result: list[PatientPortalTreatmentCharge] = []
    for charge in charges:
        balance = _charge_balance(db, charge)
        if balance <= 0:
            continue
        result.append(
            PatientPortalTreatmentCharge(
                charge_entry_id=charge.id,
                amount=float(charge.amount),
                paid_amount=float(max(charge.amount - balance, Decimal("0"))),
                balance_amount=float(balance),
                currency=charge.currency,
                payment_enabled=(
                    bool(settings.razorpay_key_id and settings.razorpay_key_secret)
                    and charge.currency == settings.patient_payment_currency.upper()
                ),
            )
        )
    db.add(
        AuditEvent(
            clinic_id=patient.clinic_id,
            branch_id=patient.branch_id,
            actor_id=account.id,
            actor_type="patient",
            action="access",
            resource_type="treatment-charges",
            detail={"outstandingCount": len(result)},
        )
    )
    db.commit()
    return result


@router.post(
    "/treatment-payments/portal/orders",
    response_model=TreatmentPaymentOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient_portal_payment_order(
    request: TreatmentPaymentOrderCreate,
    account: CurrentPatient,
    db: DbSession,
) -> TreatmentPaymentOrderResponse:
    patient = _patient_for_payment_account(db, account)
    charge = (
        db.query(TreatmentLedgerEntry)
        .filter(
            TreatmentLedgerEntry.id == request.charge_entry_id,
            TreatmentLedgerEntry.clinic_id == patient.clinic_id,
            TreatmentLedgerEntry.patient_id == patient.id,
            TreatmentLedgerEntry.entry_type == "charge",
        )
        .with_for_update()
        .first()
    )
    if charge is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treatment charge not found.")
    return _create_payment_order_for_charge(
        db,
        charge,
        actor_id=account.id,
        actor_type="patient",
        initiated_by_patient=True,
    )


@router.post(
    "/treatment-payments/portal/verify",
    response_model=TreatmentPaymentVerifyResponse,
)
def verify_patient_portal_payment(
    request: VerifyPaymentRequest,
    account: CurrentPatient,
    db: DbSession,
) -> TreatmentPaymentVerifyResponse:
    patient = _patient_for_payment_account(db, account)
    order = (
        db.query(PatientPaymentOrder)
        .filter(
            PatientPaymentOrder.razorpay_order_id == request.razorpay_order_id,
            PatientPaymentOrder.clinic_id == patient.clinic_id,
            PatientPaymentOrder.patient_id == patient.id,
        )
        .with_for_update()
        .first()
    )
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treatment payment order not found.")
    return _verify_payment_order(db, order, request)


@router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request, db: DbSession) -> dict[str, str]:
    secret = settings.razorpay_webhook_secret
    if not secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Razorpay webhook is not configured.")
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    expected_signature = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid Razorpay webhook signature.")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid webhook JSON.") from exc
    if payload.get("event") != "payment.captured":
        return {"status": "ignored"}
    payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment.get("order_id")
    payment_id = payment.get("id")
    if not order_id or not payment_id or payment.get("status") != "captured":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Captured payment event is incomplete.")
    order = (
        db.query(PatientPaymentOrder)
        .filter(PatientPaymentOrder.razorpay_order_id == order_id)
        .with_for_update()
        .first()
    )
    if order is None:
        return {"status": "ignored"}
    _record_captured_payment(
        db,
        order,
        payment_id=payment_id,
        amount_subunits=payment.get("amount", 0),
        currency=payment.get("currency", ""),
    )
    return {"status": "recorded"}


def _accounting_csv_response(db: Session, current_user: CurrentUser, *, claims: bool) -> Response:
    _require_staff(current_user)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    row_count = 0
    if claims:
        writer.writerow(
            [
                "claim_id",
                "patient_id",
                "payer",
                "claim_number",
                "status",
                "billed_amount",
                "approved_amount",
                "paid_amount",
                "currency",
                "submitted_at",
                "resolved_at",
            ]
        )
        from app.models.healthcare import InsuranceClaim

        query = db.query(InsuranceClaim).filter(InsuranceClaim.clinic_id == current_user.clinic_id)
        if current_user.role == "staff" and current_user.branch_id:
            query = query.filter(InsuranceClaim.branch_id == current_user.branch_id)
        records = query.order_by(InsuranceClaim.created_at.asc()).all()
        for claim in records:
            writer.writerow(
                _spreadsheet_safe(value)
                for value in [
                    claim.id,
                    claim.patient_id,
                    claim.payer_name,
                    claim.claim_number,
                    claim.status,
                    claim.billed_amount,
                    claim.approved_amount if claim.approved_amount is not None else "",
                    claim.paid_amount,
                    claim.currency,
                    claim.submitted_at.isoformat() if claim.submitted_at else "",
                    claim.resolved_at.isoformat() if claim.resolved_at else "",
                ]
            )
            row_count += 1
        filename = "dentalpilot-insurance-claims.csv"
        resource_type = "insurance-claims-csv"
    else:
        writer.writerow(
            [
                "entry_id",
                "patient_id",
                "external_patient_reference",
                "entry_type",
                "charge_entry_id",
                "stage_id",
                "amount",
                "currency",
                "method",
                "reference",
                "created_at",
            ]
        )
        query = (
            db.query(TreatmentLedgerEntry, Patient)
            .join(Patient, Patient.id == TreatmentLedgerEntry.patient_id)
            .filter(TreatmentLedgerEntry.clinic_id == current_user.clinic_id)
        )
        if current_user.role == "staff" and current_user.branch_id:
            query = query.filter(TreatmentLedgerEntry.branch_id == current_user.branch_id)
        records = query.order_by(TreatmentLedgerEntry.created_at.asc()).all()
        for entry, patient in records:
            writer.writerow(
                _spreadsheet_safe(value)
                for value in [
                    entry.id,
                    patient.id,
                    patient.external_reference or "",
                    entry.entry_type,
                    entry.charge_entry_id or "",
                    entry.stage_id or "",
                    entry.amount,
                    entry.currency,
                    entry.method,
                    entry.reference,
                    entry.created_at.isoformat(),
                ]
            )
            row_count += 1
        filename = "dentalpilot-accounting-ledger.csv"
        resource_type = "treatment-ledger-csv"

    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            branch_id=current_user.branch_id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="export",
            resource_type=resource_type,
            detail={"rowCount": row_count},
        )
    )
    db.commit()
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/accounting/ledger.csv")
def export_accounting_ledger(current_user: CurrentUser, db: DbSession) -> Response:
    return _accounting_csv_response(db, current_user, claims=False)


@router.get("/accounting/insurance-claims.csv")
def export_accounting_claims(current_user: CurrentUser, db: DbSession) -> Response:
    return _accounting_csv_response(db, current_user, claims=True)


@router.post("/pms/reconcile")
async def reconcile_pms_csv(
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    field_mapping: str = Form(
        '{"transactionReference":"Transaction ID","patientReference":"Patient ID",'
        '"entryType":"Type","amount":"Amount","currency":"Currency"}'
    ),
) -> dict[str, int | str]:
    _require_staff(current_user)
    content = await file.read(MAX_RECONCILIATION_FILE_BYTES + 1)
    if not content or len(content) > MAX_RECONCILIATION_FILE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "Upload a non-empty CSV file smaller than 5 MB.",
        )
    try:
        mapping = json.loads(field_mapping)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Field mapping must be valid JSON.") from exc
    if (
        not isinstance(mapping, dict)
        or set(mapping) != RECONCILIATION_FIELDS
        or not all(isinstance(value, str) and value for value in mapping.values())
        or len(set(mapping.values())) != len(mapping)
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Map each required reconciliation field to a distinct CSV column.",
        )
    try:
        source_rows = REGISTRY.resolve("provider-neutral-csv").parse_rows(
            IntegrationContext(
                clinic_id=current_user.clinic_id,
                branch_id=current_user.branch_id,
                actor_id=current_user.id,
            ),
            content,
            mapping,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if not source_rows or len(source_rows) > MAX_RECONCILIATION_ROWS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"CSV must contain between 1 and {MAX_RECONCILIATION_ROWS} data rows.",
        )
    from app.models.healthcare import PmsReconciliationRow, PmsReconciliationRun

    local_query = (
        db.query(TreatmentLedgerEntry, Patient)
        .join(Patient, Patient.id == TreatmentLedgerEntry.patient_id)
        .filter(TreatmentLedgerEntry.clinic_id == current_user.clinic_id)
    )
    if current_user.role == "staff" and current_user.branch_id:
        local_query = local_query.filter(TreatmentLedgerEntry.branch_id == current_user.branch_id)
    local_records = local_query.all()
    local_by_reference: dict[str, list[tuple[TreatmentLedgerEntry, Patient]]] = {}
    for entry, patient in local_records:
        if entry.reference:
            local_by_reference.setdefault(entry.reference, []).append((entry, patient))

    from pathlib import PurePath

    run = PmsReconciliationRun(
        clinic_id=current_user.clinic_id,
        branch_id=current_user.branch_id,
        filename=PurePath((file.filename or "pms-export.csv").replace("\\", "/")).name,
        total_rows=len(source_rows),
        created_by=current_user.id,
    )
    db.add(run)
    db.flush()
    seen_references: set[str] = set()
    matched_references: set[str] = set()
    for row_number, row in enumerate(source_rows, start=2):
        transaction_reference = row["transactionReference"]
        patient_reference = row["patientReference"]
        entry_type = row["entryType"].lower()
        currency = row["currency"].upper()
        amount_text = row["amount"]
        external_amount: Decimal | None = None
        detail = ""
        if transaction_reference in seen_references:
            row_status = "duplicate-source"
            detail = "Transaction reference appears more than once in the imported CSV."
            run.duplicate_source_rows += 1
        elif not transaction_reference or not patient_reference:
            row_status = "invalid-source"
            detail = "Transaction and patient references are required."
            run.invalid_rows += 1
        else:
            seen_references.add(transaction_reference)
            try:
                external_amount = Decimal(amount_text)
                if not external_amount.is_finite() or external_amount <= 0:
                    raise ValueError
                if external_amount.as_tuple().exponent < -2:
                    raise ValueError
                if entry_type not in {"charge", "payment", "refund"} or len(currency) != 3:
                    raise ValueError
            except (ValueError, ArithmeticError):
                row_status = "invalid-source"
                detail = "Type, amount, or ISO currency code is invalid."
                run.invalid_rows += 1
            else:
                matches = local_by_reference.get(transaction_reference, [])
                if not matches:
                    row_status = "missing-local"
                    detail = "No local ledger entry has this transaction reference."
                    run.missing_local_rows += 1
                elif len(matches) > 1:
                    row_status = "duplicate-local"
                    detail = "Multiple local ledger entries use this transaction reference."
                    run.mismatch_rows += 1
                else:
                    local_entry, local_patient = matches[0]
                    patient_identifiers = {local_patient.id}
                    if local_patient.external_reference:
                        patient_identifiers.add(local_patient.external_reference)
                    matched_references.add(transaction_reference)
                    mismatch_fields = []
                    if patient_reference not in patient_identifiers:
                        mismatch_fields.append("patient reference")
                    if entry_type != local_entry.entry_type:
                        mismatch_fields.append("entry type")
                    if external_amount != local_entry.amount:
                        mismatch_fields.append("amount")
                    if currency != local_entry.currency:
                        mismatch_fields.append("currency")
                    if mismatch_fields:
                        row_status = "mismatch"
                        detail = "Values differ: " + ", ".join(mismatch_fields) + "."
                        run.mismatch_rows += 1
                    else:
                        row_status = "matched"
                        detail = "PMS row matches the clinic ledger."
                        run.matched_rows += 1
                    db.add(
                        PmsReconciliationRow(
                            run_id=run.id,
                            clinic_id=current_user.clinic_id,
                            row_number=row_number,
                            status=row_status,
                            transaction_reference=transaction_reference,
                            patient_reference=patient_reference,
                            local_ledger_entry_id=local_entry.id,
                            entry_type=entry_type,
                            external_amount=external_amount,
                            local_amount=local_entry.amount,
                            currency=currency,
                            details=detail,
                        )
                    )
                    continue
        matches = local_by_reference.get(transaction_reference, [])
        local_entry = matches[0][0] if len(matches) == 1 else None
        db.add(
            PmsReconciliationRow(
                run_id=run.id,
                clinic_id=current_user.clinic_id,
                row_number=row_number,
                status=row_status,
                transaction_reference=transaction_reference,
                patient_reference=patient_reference,
                local_ledger_entry_id=local_entry.id if local_entry else None,
                entry_type=entry_type or None,
                external_amount=external_amount,
                local_amount=local_entry.amount if local_entry else None,
                currency=currency,
                details=detail,
            )
        )

    for entry, patient in local_records:
        if not entry.reference or entry.reference in matched_references:
            continue
        run.missing_pms_rows += 1
        db.add(
            PmsReconciliationRow(
                run_id=run.id,
                clinic_id=current_user.clinic_id,
                row_number=None,
                status="missing-pms",
                transaction_reference=entry.reference,
                patient_reference=patient.external_reference or patient.id,
                local_ledger_entry_id=entry.id,
                entry_type=entry.entry_type,
                local_amount=entry.amount,
                currency=entry.currency,
                details="Local ledger entry is absent from the uploaded PMS CSV.",
            )
        )
    db.add(
        AuditEvent(
            clinic_id=current_user.clinic_id,
            branch_id=current_user.branch_id,
            actor_id=current_user.id,
            actor_type=current_user.role,
            action="reconcile",
            resource_type="pms-csv",
            resource_id=run.id,
            detail={
                "matched": run.matched_rows,
                "mismatched": run.mismatch_rows,
                "missingLocal": run.missing_local_rows,
                "missingPms": run.missing_pms_rows,
                "invalid": run.invalid_rows,
            },
        )
    )
    db.commit()
    return {
        "id": run.id,
        "totalRows": run.total_rows,
        "matchedRows": run.matched_rows,
        "mismatchRows": run.mismatch_rows,
        "missingLocalRows": run.missing_local_rows,
        "missingPmsRows": run.missing_pms_rows,
        "duplicateSourceRows": run.duplicate_source_rows,
        "invalidRows": run.invalid_rows,
    }


@router.get("/pms/reconciliation-runs")
def list_pms_reconciliation_runs(current_user: CurrentUser, db: DbSession) -> list[dict]:
    _require_staff(current_user)
    from app.models.healthcare import PmsReconciliationRun

    query = db.query(PmsReconciliationRun).filter(
        PmsReconciliationRun.clinic_id == current_user.clinic_id
    )
    if current_user.role == "staff" and current_user.branch_id:
        query = query.filter(PmsReconciliationRun.branch_id == current_user.branch_id)
    runs = query.order_by(PmsReconciliationRun.created_at.desc()).limit(100).all()
    return [
        {
            "id": run.id,
            "filename": run.filename,
            "totalRows": run.total_rows,
            "matchedRows": run.matched_rows,
            "mismatchRows": run.mismatch_rows,
            "missingLocalRows": run.missing_local_rows,
            "missingPmsRows": run.missing_pms_rows,
            "duplicateSourceRows": run.duplicate_source_rows,
            "invalidRows": run.invalid_rows,
            "createdAt": run.created_at,
        }
        for run in runs
    ]


@router.get("/pms/reconciliation-runs/{run_id}/rows")
def list_pms_reconciliation_rows(
    run_id: str, current_user: CurrentUser, db: DbSession
) -> list[dict]:
    _require_staff(current_user)
    from app.models.healthcare import PmsReconciliationRow, PmsReconciliationRun

    run_query = db.query(PmsReconciliationRun).filter(
        PmsReconciliationRun.id == run_id,
        PmsReconciliationRun.clinic_id == current_user.clinic_id,
    )
    if current_user.role == "staff" and current_user.branch_id:
        run_query = run_query.filter(PmsReconciliationRun.branch_id == current_user.branch_id)
    if run_query.first() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reconciliation run not found.")
    rows = (
        db.query(PmsReconciliationRow)
        .filter(
            PmsReconciliationRow.run_id == run_id,
            PmsReconciliationRow.clinic_id == current_user.clinic_id,
        )
        .order_by(PmsReconciliationRow.row_number.asc().nullslast())
        .all()
    )
    return [
        {
            "id": row.id,
            "rowNumber": row.row_number,
            "status": row.status,
            "transactionReference": row.transaction_reference,
            "patientReference": row.patient_reference,
            "localLedgerEntryId": row.local_ledger_entry_id,
            "entryType": row.entry_type,
            "externalAmount": float(row.external_amount) if row.external_amount is not None else None,
            "localAmount": float(row.local_amount) if row.local_amount is not None else None,
            "currency": row.currency,
            "details": row.details,
        }
        for row in rows
    ]
