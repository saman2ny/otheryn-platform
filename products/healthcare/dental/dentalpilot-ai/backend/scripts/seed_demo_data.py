"""Seed fictional demo data for the local Bright Smile Dental demo clinic.

Local/demo only. Refuses to run when APP_ENVIRONMENT=production.
Idempotent: safe to run repeatedly; existing demo rows are reused.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.calendar import CalendarEvent
from app.models.clinic import Clinic
from app.models.content import GeneratedContent
from app.models.healthcare import ClinicBranch, HealthRecord, Patient

DEMO_PATIENTS = [
    {"full_name": "Demo Patient One", "email": "demo.patient1@example.com", "phone": "555-0101"},
    {"full_name": "Demo Patient Two", "email": "demo.patient2@example.com", "phone": "555-0102"},
    {"full_name": "Demo Patient Three", "email": "demo.patient3@example.com", "phone": "555-0103"},
]


def main() -> None:
    if settings.app_environment == "production":
        raise SystemExit("Refusing to seed demo data in production.")

    db = SessionLocal()
    try:
        clinic = (
            db.query(Clinic)
            .filter(Clinic.name == "Bright Smile Dental (Demo)")
            .first()
        )
        if clinic is None:
            raise SystemExit(
                "Demo clinic 'Bright Smile Dental (Demo)' not found. "
                "Run scripts/seed_hierarchy.py first."
            )

        branch = (
            db.query(ClinicBranch)
            .filter(ClinicBranch.clinic_id == clinic.id)
            .first()
        )
        branch_id = branch.id if branch else None

        created_patients = 0
        for item in DEMO_PATIENTS:
            exists = (
                db.query(Patient)
                .filter(
                    Patient.clinic_id == clinic.id,
                    Patient.email == item["email"],
                )
                .first()
            )
            if exists is not None:
                continue
            db.add(
                Patient(
                    clinic_id=clinic.id,
                    branch_id=branch_id,
                    consent_channel="email",
                    **item,
                )
            )
            created_patients += 1

        content = (
            db.query(GeneratedContent)
            .filter(
                GeneratedContent.clinic_id == clinic.id,
                GeneratedContent.topic == "Demo launch",
            )
            .first()
        )
        if content is None:
            content = GeneratedContent(
                clinic_id=clinic.id,
                platform="instagram",
                tone="friendly",
                topic="Demo launch",
                headline="Welcome to Bright Smile Dental",
                body="A fictional demo post used only for local development.",
                hashtags=["dental", "demo"],
                status="ready",
            )
            db.add(content)
            db.flush()

        event = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.clinic_id == clinic.id,
                CalendarEvent.title == "Demo launch post",
            )
            .first()
        )
        if event is None:
            db.add(
                CalendarEvent(
                    clinic_id=clinic.id,
                    content_id=content.id,
                    title="Demo launch post",
                    platform="instagram",
                    scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
                    status="scheduled",
                )
            )

        patient = (
            db.query(Patient)
            .filter(
                Patient.clinic_id == clinic.id,
                Patient.email == "demo.patient1@example.com",
            )
            .first()
        )
        if patient is not None and not (
            db.query(HealthRecord)
            .filter(HealthRecord.patient_id == patient.id)
            .first()
        ):
            db.add(
                HealthRecord(
                    clinic_id=clinic.id,
                    patient_id=patient.id,
                    record_type="document",
                    title="Demo treatment report",
                    source_name="Demo Clinic",
                    author_name="Dr. Demo",
                    provenance_hash=hashlib.sha256(b"demo-health-record").hexdigest(),
                    metadata_json={"demo": True},
                )
            )

        db.commit()
        print(
            f"Demo data ready: {created_patients} new patients, "
            "1 demo post, 1 scheduled event, 1 demo health record."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()