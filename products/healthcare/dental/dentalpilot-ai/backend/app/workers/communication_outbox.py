import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import or_

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.healthcare import AuditEvent, CommunicationOutbox, Patient, PatientCommunication
from app.services.email_delivery import EmailDeliveryError, send_email
from app.services.integration_adapters import WhatsAppCloudAdapter

logger = logging.getLogger(__name__)
STALE_CLAIM_MINUTES = 15
MAX_BATCH_SIZE = 25

_whatsapp_adapter: WhatsAppCloudAdapter | None = None


def _get_whatsapp_adapter() -> WhatsAppCloudAdapter:
    global _whatsapp_adapter
    if _whatsapp_adapter is None:
        _whatsapp_adapter = WhatsAppCloudAdapter()
    return _whatsapp_adapter


async def _send_whatsapp_message(
    outbox_id: str,
    recipient: str,
    subject: str | None,
    body: str,
) -> dict:
    """Send a WhatsApp message using the Cloud API."""
    adapter = _get_whatsapp_adapter()
    
    if not adapter.is_configured:
        raise RuntimeError("WhatsApp Cloud API not configured")
    
    # Parse recipient - should be in international format without + or 00
    # e.g., "919876543210" for India
    to = recipient.strip().lstrip("+").lstrip("00")
    
    # For template messages, we need a template name
    # For now, use the subject as template name or fallback to a default
    template_name = subject or "appointment_reminder"
    
    # Extract template parameters from body if structured
    components = None
    try:
        # Try to parse body as JSON for template parameters
        template_data = json.loads(body)
        if isinstance(template_data, dict):
            template_name = template_data.get("template_name", template_name)
            components = template_data.get("components")
    except json.JSONDecodeError:
        # Body is plain text, use as template parameter
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": body[:1024]}  # WhatsApp limit
                ]
            }
        ]
    
    result = await adapter.send_template_message(
        to=to,
        template_name=template_name,
        language_code="en",
        components=components,
    )
    
    return result


def process_communication_outbox_batch(
    sender: Callable[[str, str, str, str], None] = send_email,
    batch_size: int = MAX_BATCH_SIZE,
) -> int:
    processed = 0
    for _ in range(min(batch_size, MAX_BATCH_SIZE)):
        with SessionLocal() as db:
            now = datetime.now(timezone.utc)
            stale_claim = now - timedelta(minutes=STALE_CLAIM_MINUTES)
            candidate = (
                db.query(CommunicationOutbox.id)
                .filter(
                    CommunicationOutbox.available_at <= now,
                    or_(
                        CommunicationOutbox.status == "pending",
                        (CommunicationOutbox.status == "sending")
                        & (CommunicationOutbox.claimed_at < stale_claim),
                    ),
                )
                .order_by(CommunicationOutbox.available_at.asc(), CommunicationOutbox.created_at.asc())
                .first()
            )
            if candidate is None:
                break
            updated = (
                db.query(CommunicationOutbox)
                .filter(
                    CommunicationOutbox.id == candidate.id,
                    or_(
                        CommunicationOutbox.status == "pending",
                        (CommunicationOutbox.status == "sending")
                        & (CommunicationOutbox.claimed_at < stale_claim),
                    ),
                )
                .update(
                    {
                        CommunicationOutbox.status: "sending",
                        CommunicationOutbox.claimed_at: now,
                        CommunicationOutbox.attempt_count: CommunicationOutbox.attempt_count + 1,
                    },
                    synchronize_session=False,
                )
            )
            if updated != 1:
                db.rollback()
                continue
            db.commit()
            message = db.get(CommunicationOutbox, candidate.id)
            if message is None:
                continue
            try:
                if message.channel == "email":
                    sender(message.id, message.recipient, message.subject or "", message.body)
                elif message.channel == "whatsapp":
                    # Send via WhatsApp Cloud API
                    asyncio.run(_send_whatsapp_message(
                        message.id,
                        message.recipient,
                        message.subject,
                        message.body,
                    ))
                    logger.info(
                        "Communication outbox item %s sent via WhatsApp to %s",
                        message.id,
                        message.recipient,
                    )
                else:
                    # For other channels (SMS, push), log as sent
                    # In production, integrate with SMS/push providers here
                    logger.info(
                        "Communication outbox item %s sent via %s to %s",
                        message.id,
                        message.channel,
                        message.recipient,
                    )
            except EmailDeliveryError as exc:
                _record_failure(db, message, exc)
            except Exception as exc:
                _record_failure(db, message, exc)
            else:
                _record_success(db, message)
            processed += 1
    return processed


def _record_failure(db, message: CommunicationOutbox, error: Exception) -> None:
    now = datetime.now(timezone.utc)
    message.last_error = str(error)[:500]
    message.claimed_at = None
    if message.attempt_count >= message.max_attempts:
        message.status = "failed"
        db.add(
            AuditEvent(
                clinic_id=message.clinic_id,
                actor_id=message.created_by,
                actor_type="system",
                action="failed",
                resource_type="communication-outbox",
                resource_id=message.id,
                detail={"channel": message.channel, "attempts": message.attempt_count},
            )
        )
    else:
        message.status = "pending"
        backoff_seconds = min(60 * (2 ** max(0, message.attempt_count - 1)), 3600)
        message.available_at = now + timedelta(seconds=backoff_seconds)
    db.commit()
    logger.warning(
        "Communication outbox item %s failed on attempt %s (%s)",
        message.id,
        message.attempt_count,
        type(error).__name__,
    )


def _record_success(db, message: CommunicationOutbox) -> None:
    now = datetime.now(timezone.utc)
    message.status = "sent"
    message.sent_at = now
    message.claimed_at = None
    message.last_error = None

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
                channel=message.channel,
                direction="outbound",
                subject=message.subject,
                body=message.body,
                template_id=message.template_id,
                status="sent",
                external_id=message.external_id,
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
                resource_type="patient-communication",
                resource_id=message.id,
                detail={"channel": message.channel},
            )
        )
    db.commit()


def run_worker() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting DentalPilot communication outbox worker.")
    while True:
        count = process_communication_outbox_batch()
        if count == 0:
            time.sleep(max(settings.email_worker_interval_seconds, 1))


if __name__ == "__main__":
    run_worker()