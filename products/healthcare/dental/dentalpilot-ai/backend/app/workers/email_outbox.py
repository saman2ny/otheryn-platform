import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import or_

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.healthcare import AuditEvent, EmailOutbox, Patient, PatientCommunication, RecallReminder
from app.services.email_delivery import EmailDeliveryError, send_email

logger = logging.getLogger(__name__)
STALE_CLAIM_MINUTES = 15
MAX_BATCH_SIZE = 25


def process_email_outbox_batch(
    sender: Callable[[str, str, str, str], None] = send_email,
    batch_size: int = MAX_BATCH_SIZE,
) -> int:
    processed = 0
    for _ in range(min(batch_size, MAX_BATCH_SIZE)):
        with SessionLocal() as db:
            now = datetime.now(timezone.utc)
            stale_claim = now - timedelta(minutes=STALE_CLAIM_MINUTES)
            candidate = (
                db.query(EmailOutbox.id)
                .filter(
                    EmailOutbox.available_at <= now,
                    or_(
                        EmailOutbox.status == "pending",
                        (EmailOutbox.status == "sending")
                        & (EmailOutbox.claimed_at < stale_claim),
                    ),
                )
                .order_by(EmailOutbox.available_at.asc(), EmailOutbox.created_at.asc())
                .first()
            )
            if candidate is None:
                break
            updated = (
                db.query(EmailOutbox)
                .filter(
                    EmailOutbox.id == candidate.id,
                    or_(
                        EmailOutbox.status == "pending",
                        (EmailOutbox.status == "sending")
                        & (EmailOutbox.claimed_at < stale_claim),
                    ),
                )
                .update(
                    {
                        EmailOutbox.status: "sending",
                        EmailOutbox.claimed_at: now,
                        EmailOutbox.attempt_count: EmailOutbox.attempt_count + 1,
                    },
                    synchronize_session=False,
                )
            )
            if updated != 1:
                db.rollback()
                continue
            db.commit()
            message = db.get(EmailOutbox, candidate.id)
            if message is None:
                continue
            try:
                sender(message.id, message.recipient_email, message.subject, message.body_text)
            except EmailDeliveryError as exc:
                _record_failure(db, message, exc)
            else:
                _record_success(db, message)
            processed += 1
    return processed


def _record_failure(db, message: EmailOutbox, error: Exception) -> None:
    now = datetime.now(timezone.utc)
    message.last_error = str(error)[:500]
    message.claimed_at = None
    if message.attempt_count >= settings.email_max_attempts:
        message.status = "failed"
        _set_reminder_status(db, message.reminder_id, "failed")
        db.add(
            AuditEvent(
                clinic_id=message.clinic_id,
                actor_id=message.created_by,
                actor_type="system",
                action="failed",
                resource_type="email",
                resource_id=message.id,
                detail={"attempts": message.attempt_count},
            )
        )
    else:
        message.status = "pending"
        backoff_seconds = min(60 * (2 ** max(0, message.attempt_count - 1)), 3600)
        message.available_at = now + timedelta(seconds=backoff_seconds)
    db.commit()
    logger.warning(
        "Email outbox item %s failed on attempt %s (%s)",
        message.id,
        message.attempt_count,
        type(error).__name__,
    )


def _record_success(db, message: EmailOutbox) -> None:
    now = datetime.now(timezone.utc)
    message.status = "sent"
    message.sent_at = now
    message.claimed_at = None
    message.last_error = None
    reminder = _set_reminder_status(db, message.reminder_id, "sent")
    patient = (
        db.query(Patient)
        .filter(Patient.id == message.patient_id, Patient.clinic_id == message.clinic_id)
        .first()
    )
    if patient is not None:
        db.add(
            PatientCommunication(
                clinic_id=message.clinic_id,
                patient_id=patient.id,
                channel="email",
                direction="outbound",
                subject=message.subject,
                body=message.body_text,
                status="sent",
                actor_id=message.created_by,
                sent_at=now,
            )
        )
        db.add(
            AuditEvent(
                clinic_id=message.clinic_id,
                branch_id=patient.branch_id,
                actor_id=message.created_by,
                actor_type="staff",
                action="send",
                resource_type="patient-email",
                resource_id=message.id,
                detail={"reminderId": reminder.id if reminder else None},
            )
        )
    db.commit()


def _set_reminder_status(db, reminder_id: str | None, reminder_status: str) -> RecallReminder | None:
    if reminder_id is None:
        return None
    reminder = db.get(RecallReminder, reminder_id)
    if reminder is not None:
        reminder.status = reminder_status
    return reminder


def run_worker() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting DentalPilot email outbox worker.")
    while True:
        count = process_email_outbox_batch()
        if count == 0:
            time.sleep(max(settings.email_worker_interval_seconds, 1))


if __name__ == "__main__":
    run_worker()
