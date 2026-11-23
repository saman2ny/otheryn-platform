from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Clinic, EmailOutbox, Patient
from app.services.email_delivery import EmailDeliveryError
from app.workers import email_outbox


@pytest.fixture()
def session_factory(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(email_outbox, "SessionLocal", test_session_factory)
    yield test_session_factory
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_email_outbox_sends_and_retries_with_a_fake_sender(session_factory):
    now = datetime.now(timezone.utc)
    with session_factory() as db:
        clinic = Clinic(name="Outbox clinic", plan_tier="free")
        db.add(clinic)
        db.flush()
        patient = Patient(
            clinic_id=clinic.id,
            full_name="Outbox patient",
            email="patient@example.com",
        )
        db.add(patient)
        db.flush()
        sent = EmailOutbox(
            clinic_id=clinic.id,
            patient_id=patient.id,
            recipient_email=patient.email,
            subject="Appointment details",
            body_text="Your visit is confirmed.",
            available_at=now - timedelta(seconds=1),
            created_by="test-user",
        )
        retry = EmailOutbox(
            clinic_id=clinic.id,
            patient_id=patient.id,
            recipient_email=patient.email,
            subject="Follow-up",
            body_text="Please contact the clinic.",
            available_at=now - timedelta(seconds=1),
            created_by="test-user",
        )
        db.add_all([sent, retry])
        db.commit()
        sent_id, retry_id = sent.id, retry.id

    delivered_ids: list[str] = []

    def fake_sender(outbox_id: str, recipient: str, subject: str, body_text: str) -> None:
        delivered_ids.append(outbox_id)
        if subject == "Follow-up":
            raise EmailDeliveryError("Temporary test failure.")

    assert email_outbox.process_email_outbox_batch(sender=fake_sender) == 2
    assert len(delivered_ids) == 2

    with session_factory() as db:
        sent_message = db.get(EmailOutbox, sent_id)
        retry_message = db.get(EmailOutbox, retry_id)
        assert sent_message.status == "sent"
        assert sent_message.attempt_count == 1
        assert sent_message.sent_at is not None
        assert retry_message.status == "pending"
        assert retry_message.attempt_count == 1
        assert retry_message.last_error == "Temporary test failure."
        assert retry_message.available_at.replace(tzinfo=timezone.utc) > now
