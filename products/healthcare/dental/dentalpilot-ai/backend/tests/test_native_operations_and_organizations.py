from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.clinic import Clinic
from app.models.organization import OrganizationInvitation
from app.models.user import User
from app.routers import operations as operations_router


@pytest.fixture()
def workspace():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with session_factory() as db:
        clinic = Clinic(name="Native Operations Clinic", plan_tier="free")
        db.add(clinic)
        db.flush()
        owner = User(
            email="native-owner@example.com",
            hashed_password=hash_password("test-password"),
            full_name="Native Owner",
            role="owner",
            clinic_id=clinic.id,
        )
        db.add(owner)
        db.commit()
        clinic_id = clinic.id
        owner_id = owner.id

    def override_get_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(
        app,
        headers={"Authorization": f"Bearer {create_access_token(owner_id)}"},
    ) as client:
        yield client, session_factory, clinic_id, owner_id
    app.dependency_overrides.clear()
    engine.dispose()


def test_digital_case_asset_maintenance_and_sterilization_are_audited(workspace):
    client, _, _, _ = workspace
    branch_response = client.post(
        "/api/v1/clinic/branches",
        json={"name": "Main", "address": "1 Dental Way", "phone": "555-0101"},
    )
    assert branch_response.status_code == 201
    branch = branch_response.json()

    patient_response = client.post(
        "/api/v1/healthcare/patients",
        json={"fullName": "Case Patient", "branchId": branch["id"]},
    )
    assert patient_response.status_code == 201
    patient = patient_response.json()

    case = client.post(
        "/api/v1/operations/dental-cases",
        json={
            "patientId": patient["id"],
            "branchId": branch["id"],
            "caseType": "cad-cam",
            "title": "Crown production",
            "providerName": "Local dental lab",
            "details": {"tooth": "36"},
        },
    )
    assert case.status_code == 201
    case_id = case.json()["id"]
    invalid_transition = client.patch(
        f"/api/v1/operations/dental-cases/{case_id}",
        json={"status": "completed"},
    )
    assert invalid_transition.status_code == 409
    planning = client.patch(
        f"/api/v1/operations/dental-cases/{case_id}",
        json={"status": "planning"},
    )
    assert planning.status_code == 200

    asset_response = client.post(
        "/api/v1/operations/assets",
        json={
            "branchId": branch["id"],
            "assetTag": "AUTO-001",
            "assetType": "autoclave",
            "displayName": "Sterilizer 1",
            "nextServiceAt": "2027-01-15T10:00:00+00:00",
        },
    )
    assert asset_response.status_code == 201
    asset = asset_response.json()
    cycle = client.post(
        "/api/v1/operations/sterilization-cycles",
        json={
            "branchId": branch["id"],
            "assetId": asset["id"],
            "cycleReference": "CYCLE-001",
            "loadReference": "LOAD-001",
            "result": "failed",
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "operatorName": "Clinic staff",
        },
    )
    assert cycle.status_code == 201
    listed_asset = client.get("/api/v1/operations/assets").json()[0]
    assert listed_asset["status"] == "unavailable"

    maintenance = client.post(
        f"/api/v1/operations/assets/{asset['id']}/maintenance",
        json={"workType": "repair", "notes": "Check heating cycle."},
    )
    assert maintenance.status_code == 201
    in_progress = client.patch(
        f"/api/v1/operations/assets/{asset['id']}/maintenance/{maintenance.json()['id']}",
        json={"status": "in-progress", "notes": "Repair started."},
    )
    assert in_progress.status_code == 200
    completed = client.patch(
        f"/api/v1/operations/assets/{asset['id']}/maintenance/{maintenance.json()['id']}",
        json={"status": "completed", "notes": "Repair logged."},
    )
    assert completed.status_code == 200
    still_unavailable = client.get("/api/v1/operations/assets").json()[0]
    assert still_unavailable["status"] == "unavailable"


def test_clinic_organization_invitation_and_aggregate_reporting(workspace):
    client, session_factory, clinic_id, owner_id = workspace
    standalone = client.get("/api/v1/organizations/current")
    assert standalone.status_code == 200
    assert standalone.json() is None

    created = client.post("/api/v1/organizations", json={"name": "Northstar Dental Group"})
    assert created.status_code == 201
    organization = created.json()
    assert organization["clinicCount"] == 1
    assert organization["currentMemberRole"] == "organization-owner"

    invited = client.post(
        "/api/v1/organizations/current/invitations",
        json={"email": "second-owner@example.com"},
    )
    assert invited.status_code == 201
    invitation = invited.json()
    assert len(invitation["invitationToken"]) >= 32
    with session_factory() as db:
        stored = db.get(OrganizationInvitation, invitation["id"])
        assert stored is not None
        assert stored.token_hash != invitation["invitationToken"]

        second_clinic = Clinic(name="Second Clinic", plan_tier="free")
        db.add(second_clinic)
        db.flush()
        second_owner = User(
            email="second-owner@example.com",
            hashed_password=hash_password("test-password"),
            full_name="Second Owner",
            role="owner",
            clinic_id=second_clinic.id,
        )
        db.add(second_owner)
        db.commit()
        second_clinic_id = second_clinic.id
        second_owner_id = second_owner.id

    second_headers = {"Authorization": f"Bearer {create_access_token(second_owner_id)}"}
    accepted = client.post(
        "/api/v1/organizations/invitations/accept",
        json={"invitationToken": invitation["invitationToken"]},
        headers=second_headers,
    )
    assert accepted.status_code == 204

    second_clinic_group = client.get(
        "/api/v1/organizations/current",
        headers=second_headers,
    )
    assert second_clinic_group.status_code == 200
    assert second_clinic_group.json()["id"] == organization["id"]
    assert second_clinic_group.json()["currentMemberRole"] == "reporting-only"

    for headers, clinic_name, currency, charge_amount, payment_amount, refund_amount in (
        ({}, "Native Operations Clinic", "INR", 100, 40, 5),
        (second_headers, "Second Clinic", "USD", 80, 20, 4),
    ):
        patient = client.post(
            "/api/v1/healthcare/patients",
            json={"fullName": f"{clinic_name} Patient"},
            headers=headers,
        )
        assert patient.status_code == 201
        charge = client.post(
            "/api/v1/healthcare/treatment-ledger",
            json={
                "patientId": patient.json()["id"],
                "entryType": "charge",
                "amount": charge_amount,
                "currency": currency,
            },
            headers=headers,
        )
        assert charge.status_code == 201
        for entry_type, amount in (("payment", payment_amount), ("refund", refund_amount)):
            ledger_entry = client.post(
                "/api/v1/healthcare/treatment-ledger",
                json={
                    "patientId": patient.json()["id"],
                    "chargeEntryId": charge.json()["id"],
                    "entryType": entry_type,
                    "amount": amount,
                    "currency": currency,
                },
                headers=headers,
            )
            assert ledger_entry.status_code == 201

    analytics = client.get("/api/v1/organizations/current/analytics")
    assert analytics.status_code == 200
    assert analytics.json()["clinicCount"] == 2
    assert {clinic["clinicName"] for clinic in analytics.json()["clinics"]} == {
        "Native Operations Clinic",
        "Second Clinic",
    }
    financials = {item["currency"]: item for item in analytics.json()["financials"]}
    assert financials["INR"] == {
        "currency": "INR",
        "clinicCount": 1,
        "chargesValue": 100,
        "paymentsReceived": 40,
        "refundsValue": 5,
        "netCollected": 35,
        "outstandingBalance": 65,
    }
    assert financials["USD"] == {
        "currency": "USD",
        "clinicCount": 1,
        "chargesValue": 80,
        "paymentsReceived": 20,
        "refundsValue": 4,
        "netCollected": 16,
        "outstandingBalance": 64,
    }
    by_clinic = {clinic["clinicName"]: clinic for clinic in analytics.json()["clinics"]}
    assert by_clinic["Second Clinic"]["financials"][0]["currency"] == "USD"

    role_path = f"/api/v1/organizations/current/members/{second_owner_id}/role"
    reporting_role = client.patch(role_path, json={"role": "reporting-only"})
    assert reporting_role.status_code == 200
    assert reporting_role.json()["role"] == "reporting-only"
    assert client.get("/api/v1/organizations/current/analytics", headers=second_headers).status_code == 200
    assert client.get("/api/v1/organizations/current/members", headers=second_headers).status_code == 403
    denied_invitation = client.post(
        "/api/v1/organizations/current/invitations",
        json={"email": "third-owner@example.com"},
        headers=second_headers,
    )
    assert denied_invitation.status_code == 403
    denied_role_change = client.patch(
        f"/api/v1/organizations/current/members/{owner_id}/role",
        json={"role": "reporting-only"},
        headers=second_headers,
    )
    assert denied_role_change.status_code == 403

    admin_role = client.patch(role_path, json={"role": "organization-admin"})
    assert admin_role.status_code == 200
    assert client.get("/api/v1/organizations/current/members", headers=second_headers).status_code == 200
    admin_invitation = client.post(
        "/api/v1/organizations/current/invitations",
        json={"email": "third-owner@example.com"},
        headers=second_headers,
    )
    assert admin_invitation.status_code == 201
    denied_admin_role_change = client.patch(
        f"/api/v1/organizations/current/members/{owner_id}/role",
        json={"role": "reporting-only"},
        headers=second_headers,
    )
    assert denied_admin_role_change.status_code == 403
    denied_admin_removal = client.delete(
        f"/api/v1/organizations/current/members/{owner_id}",
        headers=second_headers,
    )
    assert denied_admin_removal.status_code == 403
    owner_role_change = client.patch(
        f"/api/v1/organizations/current/members/{owner_id}/role",
        json={"role": "reporting-only"},
    )
    assert owner_role_change.status_code == 409
    owner_removal = client.delete(f"/api/v1/organizations/current/members/{owner_id}")
    assert owner_removal.status_code == 409

    second_accept = client.post(
        "/api/v1/organizations/invitations/accept",
        json={"invitationToken": invitation["invitationToken"]},
        headers=second_headers,
    )
    assert second_accept.status_code == 400

    removed = client.delete(f"/api/v1/organizations/current/members/{second_owner_id}")
    assert removed.status_code == 204
    second_clinic_group = client.get("/api/v1/organizations/current", headers=second_headers)
    assert second_clinic_group.status_code == 200
    assert second_clinic_group.json() is None
    with session_factory() as db:
        detached_clinic = db.get(Clinic, second_clinic_id)
        assert detached_clinic is not None
        assert detached_clinic.organization_id is None
        assert db.get(Clinic, clinic_id).organization_id == organization["id"]


def test_message_publication_note_review_and_provider_catalog_boundaries(workspace):
    client, _, _, _ = workspace
    patient_response = client.post(
        "/api/v1/healthcare/patients",
        json={
            "fullName": "Workflow Patient",
            "email": "workflow-patient@example.com",
            "consentChannel": "email",
        },
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    draft_payload = {
        "patientId": patient_id,
        "channel": "email",
        "subject": "Follow-up",
        "body": "Please contact the clinic to arrange your next visit.",
        "consentConfirmed": True,
    }
    no_consent = client.post(
        "/api/v1/operations/message-drafts",
        json={**draft_payload, "consentConfirmed": False},
    )
    assert no_consent.status_code == 400
    draft = client.post("/api/v1/operations/message-drafts", json=draft_payload)
    assert draft.status_code == 201
    approved_draft = client.patch(
        f"/api/v1/operations/message-drafts/{draft.json()['id']}",
        json={"status": "approved"},
    )
    assert approved_draft.status_code == 200
    assert approved_draft.json()["status"] == "approved"
    assert client.get("/api/v1/healthcare/email-outbox").json() == []

    publication = client.post(
        "/api/v1/operations/marketing-publications",
        json={"title": "Clinic update", "platform": "other", "body": "Draft copy"},
    )
    assert publication.status_code == 201
    direct_publish = client.patch(
        f"/api/v1/operations/marketing-publications/{publication.json()['id']}",
        json={"status": "published"},
    )
    assert direct_publish.status_code == 409
    approved_publication = client.patch(
        f"/api/v1/operations/marketing-publications/{publication.json()['id']}",
        json={"status": "approved"},
    )
    assert approved_publication.status_code == 200
    missing_schedule = client.patch(
        f"/api/v1/operations/marketing-publications/{publication.json()['id']}",
        json={"status": "scheduled"},
    )
    assert missing_schedule.status_code == 400

    note = client.post(
        "/api/v1/operations/clinical-note-drafts",
        json={
            "patientId": patient_id,
            "title": "Visit note",
            "clinicianInput": "Clinician-authored notes for the patient's visit.",
        },
    )
    assert note.status_code == 201
    reviewed = client.patch(
        f"/api/v1/operations/clinical-note-drafts/{note.json()['id']}/review",
        json={"reviewStatus": "approved"},
    )
    assert reviewed.status_code == 200
    repeated_review = client.patch(
        f"/api/v1/operations/clinical-note-drafts/{note.json()['id']}/review",
        json={"reviewStatus": "rejected"},
    )
    assert repeated_review.status_code == 409

    catalog = client.get("/api/v1/integrations/catalog")
    assert catalog.status_code == 200
    entries = {item["providerId"]: item for item in catalog.json()}
    assert entries["provider-neutral-csv"]["enabled"] is True
    assert entries["open-dental"]["enabled"] is False


def test_ai_note_drafting_is_gated_and_requires_patient_consent(workspace, monkeypatch):
    client, _, _, _ = workspace
    patient_response = client.post(
        "/api/v1/healthcare/patients",
        json={
            "fullName": "Jane Example",
            "email": "jane@example.com",
            "phone": "+15550102",
        },
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]
    note_response = client.post(
        "/api/v1/operations/clinical-note-drafts",
        json={
            "patientId": patient_id,
            "title": "Dental visit",
            "clinicianInput": "Jane Example reported sensitivity in tooth 14; no diagnosis recorded.",
        },
    )
    assert note_response.status_code == 201
    note_id = note_response.json()["id"]

    unavailable = client.patch("/api/v1/clinic/clinical-ai-settings", json={"enabled": True})
    assert unavailable.status_code == 503

    monkeypatch.setattr(settings, "clinical_note_drafting_enabled", True)
    monkeypatch.setattr(settings, "clinical_ai_data_processing_approved", True)
    monkeypatch.setattr(settings, "groq_api_key", "test-groq-key")
    enabled = client.patch("/api/v1/clinic/clinical-ai-settings", json={"enabled": True})
    assert enabled.status_code == 200
    assert enabled.json() == {"enabled": True, "available": True}

    submitted_inputs: list[str] = []

    def generate_note(clinician_input: str) -> str:
        submitted_inputs.append(clinician_input)
        return "Reported sensitivity in tooth 14. [Clinician review required.]"

    monkeypatch.setattr(operations_router, "generate_clinical_note", generate_note)
    no_consent = client.post(
        f"/api/v1/operations/clinical-note-drafts/{note_id}/generate-ai",
        json={"patientConsentConfirmed": False},
    )
    assert no_consent.status_code == 400
    assert submitted_inputs == []

    generated = client.post(
        f"/api/v1/operations/clinical-note-drafts/{note_id}/generate-ai",
        json={"patientConsentConfirmed": True},
    )
    assert generated.status_code == 200
    assert generated.json()["generationSource"] == "groq"
    assert generated.json()["reviewStatus"] == "pending-review"
    assert "Jane Example" not in submitted_inputs[0]
    assert "jane@example.com" not in submitted_inputs[0]
    assert "+15550102" not in submitted_inputs[0]
