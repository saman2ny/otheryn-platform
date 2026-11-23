from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.billing import PatientPaymentOrder

PAYMENT_ORDER_TTL = timedelta(minutes=30)


def expire_stale_payment_orders(db: Session, charge_entry_id: str) -> None:
    cutoff = datetime.now(timezone.utc) - PAYMENT_ORDER_TTL
    stale_orders = (
        db.query(PatientPaymentOrder)
        .filter(
            PatientPaymentOrder.charge_entry_id == charge_entry_id,
            PatientPaymentOrder.status == "created",
            PatientPaymentOrder.created_at <= cutoff,
        )
        .with_for_update()
        .all()
    )
    for order in stale_orders:
        order.status = "expired"
    if stale_orders:
        db.flush()
