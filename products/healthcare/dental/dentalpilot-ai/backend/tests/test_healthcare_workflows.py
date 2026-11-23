import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.clinic import Clinic
from app.models.user import User
from app.routers import healthcare as healthcare_router, patient_billing as patient_billing_router
from app.services.document_storage import StoredDocument


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    clinic = Clinic(name="Bright Smile Dental", plan_tier="free")
    db.add(clinic)
    db.flush()
    user = User(
        email="owner@example.com",
        hashed_password=hash_password("password"),
        full_name="Test Owner",
        role="owner",
        clinic_id=clinic.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    def override_get_db():
        test_db = TestingSessionLocal()
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(user.id)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_endpoints_and_request_correlation(client):
    live = client.get("/health/live", headers={"X-Request-ID": "readiness-test-1"})
    assert live.status_code == 200
    assert live.json() == {"status": "alive"}
    assert live.headers["X-Request-ID"] == "readiness-test-1"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "database": "ok"}
    assert ready.headers["X-Request-ID"]


def test_healthcare_patient_plan_record_and_recovery_flow(client):
    patient_response = client.post(
        "/api/v1/healthcare/patients",
        json={"fullName": "Priya Sharma", "email": "priya@example.com", "consentChannel": "email"},
    )
    assert patient_response.status_code == 201
    patient = patient_response.json()

    plan_response = client.post(
        "/api/v1/healthcare/treatment-plans",
        json={
            "patientId": patient["id"],
            "title": "Restorative plan",
            "clinicianName": "Dr. Test",
            "estimatedValue": 30000,
            "currency": "INR",
            "stages": [
                {"name": "Initial X-ray", "estimatedValue": 1500, "status": "accepted"},
                {
                    "name": "Root canal",
                    "estimatedValue": 28500,
                    "status": "deferred",
                    "reason": "Patient wants to wait until next month.",
                },
            ],
        },
    )
    assert plan_response.status_code == 201
    plan = plan_response.json()
    assert len(plan["stages"]) == 2
    decisions = client.get(f"/api/v1/healthcare/patients/{patient['id']}/decisions")
    assert decisions.status_code == 200
    assert any(decision["decision"] == "deferred" for decision in decisions.json())

    stage_response = client.patch(
        f"/api/v1/healthcare/treatment-stages/{plan['stages'][1]['id']}",
        json={
            "status": "scheduled",
            "reason": "Patient agreed to proceed",
            "scheduledAt": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        },
    )
    assert stage_response.status_code == 200
    assert stage_response.json()["status"] == "scheduled"

    record_response = client.post(
        "/api/v1/healthcare/records",
        json={
            "patientId": patient["id"],
            "recordType": "xray",
            "title": "Dental X-ray",
            "sourceName": "Bright Smile Dental",
            "authorName": "Dr. Test",
            "metadataJson": {"date": "2026-11-20", "tooth": "36"},
        },
    )
    assert record_response.status_code == 201
    record = record_response.json()
    assert len(record["provenanceHash"]) == 64

    consent_response = client.post(
        "/api/v1/healthcare/consents",
        json={
            "patientId": patient["id"],
            "purpose": "Second-opinion review",
            "recipientName": "Independent Dentist",
            "recordIds": [record["id"]],
            "expiresAt": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        },
    )
    assert consent_response.status_code == 201
    assert consent_response.json()["revokedAt"] is None

    reminder_response = client.post(
        "/api/v1/healthcare/reminders",
        json={
            "patientId": patient["id"],
            "reminderType": "review",
            "message": "Please schedule your follow-up review.",
            "channel": "email",
            "scheduledAt": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "consentConfirmed": True,
        },
    )
    assert reminder_response.status_code == 201

    recovery = client.get("/api/v1/healthcare/revenue-recovery")
    assert recovery.status_code == 200
    assert recovery.json()["pendingStageCount"] >= 1
    assert recovery.json()["currency"] == "INR"

    audit = client.get("/api/v1/healthcare/audit")
    assert audit.status_code == 200
    assert any(event["action"] == "create" for event in audit.json())


def create_patient_charge(client, *, amount=125.00, reference="invoice-001", email=None):
    patient_response = client.post(
        "/api/v1/healthcare/patients",
        json={
            "fullName": "Payment Test Patient",
            **({"email": email, "consentChannel": "email"} if email else {}),
        },
    )
    assert patient_response.status_code == 201
    patient = patient_response.json()
    charge_response = client.post(
        "/api/v1/healthcare/treatment-ledger",
        json={
            "patientId": patient["id"],
            "entryType": "charge",
            "amount": amount,
            "currency": "INR",
            "method": "other",
            "reference": reference,
        },
    )
    assert charge_response.status_code == 201
    return patient, charge_response.json()


def test_patient_treatment_payment_order_verify_and_retry_are_idempotent(client, monkeypatch):
    _, charge = create_patient_charge(client)
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_public")
    monkeypatch.setattr(settings, "razorpay_key_secret", "test-secret")
    created_orders = []

    def create_order(**kwargs):
        created_orders.append(kwargs)
        return {"id": "order_test_001", "amount": 12500, "currency": "INR"}

    monkeypatch.setattr(patient_billing_router.razorpay_service, "create_order", create_order)
    first_order = client.post(
        "/api/v1/billing/treatment-payments/order",
        json={"chargeEntryId": charge["id"]},
    )
    retry_order = client.post(
        "/api/v1/billing/treatment-payments/order",
        json={"chargeEntryId": charge["id"]},
    )
    assert first_order.status_code == retry_order.status_code == 201
    assert first_order.json()["orderId"] == retry_order.json()["orderId"]
    assert created_orders[0]["amount_subunits"] == 12500
    assert len(created_orders) == 1

    monkeypatch.setattr(patient_billing_router.razorpay_service, "verify_signature", lambda **_: True)
    monkeypatch.setattr(
        patient_billing_router.razorpay_service,
        "fetch_payment",
        lambda payment_id: {
            "id": payment_id,
            "order_id": "order_test_001",
            "status": "captured",
            "amount": 12500,
            "currency": "INR",
        },
    )
    verify_request = {
        "razorpayOrderId": "order_test_001",
        "razorpayPaymentId": "pay_test_001",
        "razorpaySignature": "verified-by-mock",
    }
    payment = client.post("/api/v1/billing/treatment-payments/verify", json=verify_request)
    retry_payment = client.post("/api/v1/billing/treatment-payments/verify", json=verify_request)
    assert payment.status_code == retry_payment.status_code == 200
    assert payment.json()["ledgerEntryId"] == retry_payment.json()["ledgerEntryId"]
    ledger = client.get("/api/v1/healthcare/treatment-ledger").json()
    recorded = [entry for entry in ledger if entry["method"] == "razorpay"]
    assert len(recorded) == 1
    assert recorded[0]["chargeEntryId"] == charge["id"]


def test_patient_portal_can_view_and_pay_only_its_own_treatment_charges(client, monkeypatch):
    patient, charge = create_patient_charge(
        client,
        reference="portal-invoice-01",
        email="portal-patient@example.com",
    )
    _, another_charge = create_patient_charge(client, reference="other-patient-invoice")
    invitation = client.post(
        "/api/v1/patient-portal/invitations",
        json={"patientId": patient["id"]},
    )
    assert invitation.status_code == 201
    invitation_body = invitation.json()
    accepted = client.post(
        "/api/v1/patient-portal/invitations/accept",
        json={
            "invitationToken": invitation_body["invitationToken"],
            "password": "a-secure-test-password",
        },
    )
    assert accepted.status_code == 204
    login = client.post(
        "/api/v1/patient-portal/login",
        json={
            "clinicId": invitation_body["clinicId"],
            "email": patient["email"],
            "password": "a-secure-test-password",
        },
    )
    assert login.status_code == 200
    patient_headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}

    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_public")
    monkeypatch.setattr(settings, "razorpay_key_secret", "test-secret")
    charges = client.get(
        "/api/v1/billing/treatment-payments/portal/charges",
        headers=patient_headers,
    )
    assert charges.status_code == 200
    assert [item["chargeEntryId"] for item in charges.json()] == [charge["id"]]
    assert charges.json()[0]["balanceAmount"] == 125
    assert charges.json()[0]["paymentEnabled"] is True

    def create_order(**kwargs):
        assert kwargs["amount_subunits"] == 12500
        return {"id": "order_portal_001", "amount": 12500, "currency": "INR"}

    monkeypatch.setattr(patient_billing_router.razorpay_service, "create_order", create_order)
    forbidden_order = client.post(
        "/api/v1/billing/treatment-payments/portal/orders",
        json={"chargeEntryId": another_charge["id"]},
        headers=patient_headers,
    )
    assert forbidden_order.status_code == 404
    order = client.post(
        "/api/v1/billing/treatment-payments/portal/orders",
        json={"chargeEntryId": charge["id"]},
        headers=patient_headers,
    )
    assert order.status_code == 201
    assert order.json()["orderId"] == "order_portal_001"

    monkeypatch.setattr(patient_billing_router.razorpay_service, "verify_signature", lambda **_: True)
    monkeypatch.setattr(
        patient_billing_router.razorpay_service,
        "fetch_payment",
        lambda _: {
            "order_id": "order_portal_001",
            "status": "captured",
            "amount": 12500,
            "currency": "INR",
        },
    )
    verified = client.post(
        "/api/v1/billing/treatment-payments/portal/verify",
        json={
            "razorpayOrderId": "order_portal_001",
            "razorpayPaymentId": "pay_portal_001",
            "razorpaySignature": "verified-by-mock",
        },
        headers=patient_headers,
    )
    assert verified.status_code == 200
    remaining = client.get(
        "/api/v1/billing/treatment-payments/portal/charges",
        headers=patient_headers,
    )
    assert remaining.status_code == 200
    assert remaining.json() == []


def test_patient_payment_webhook_requires_signature_and_records_capture_once(client, monkeypatch):
    _, charge = create_patient_charge(client)
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_public")
    monkeypatch.setattr(settings, "razorpay_key_secret", "test-secret")
    monkeypatch.setattr(settings, "razorpay_webhook_secret", "webhook-test-secret")
    monkeypatch.setattr(
        patient_billing_router.razorpay_service,
        "create_order",
        lambda **_: {"id": "order_webhook_001", "amount": 12500, "currency": "INR"},
    )
    order = client.post(
        "/api/v1/billing/treatment-payments/order",
        json={"chargeEntryId": charge["id"]},
    )
    assert order.status_code == 201

    body = json.dumps(
        {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_webhook_001",
                        "order_id": "order_webhook_001",
                        "status": "captured",
                        "amount": 12500,
                        "currency": "INR",
                    }
                }
            },
        },
        separators=(",", ":"),
    ).encode()
    signature = hmac.new(b"webhook-test-secret", body, hashlib.sha256).hexdigest()
    webhook_url = "/api/v1/billing/razorpay/webhook"
    invalid = client.post(webhook_url, content=body, headers={"X-Razorpay-Signature": "invalid"})
    assert invalid.status_code == 400

    headers = {"X-Razorpay-Signature": signature, "Content-Type": "application/json"}
    captured = client.post(webhook_url, content=body, headers=headers)
    retried = client.post(webhook_url, content=body, headers=headers)
    assert captured.status_code == retried.status_code == 200
    assert captured.json() == {"status": "recorded"}
    assert retried.json() == {"status": "recorded"}
    ledger = client.get("/api/v1/healthcare/treatment-ledger").json()
    assert len([entry for entry in ledger if entry["method"] == "razorpay"]) == 1


def test_insurance_claim_remittances_are_linked_to_the_treatment_ledger(client):
    patient, charge = create_patient_charge(client)
    claim_response = client.post(
        "/api/v1/healthcare/insurance-claims",
        json={
            "patientId": patient["id"],
            "chargeEntryId": charge["id"],
            "payerName": "Example Dental Cover",
            "claimNumber": "CLM-1001",
            "billedAmount": 100,
            "currency": "INR",
        },
    )
    assert claim_response.status_code == 201
    claim = claim_response.json()

    submitted = client.patch(
        f"/api/v1/healthcare/insurance-claims/{claim['id']}",
        json={"status": "submitted"},
    )
    assert submitted.status_code == 200
    approved = client.patch(
        f"/api/v1/healthcare/insurance-claims/{claim['id']}",
        json={"status": "partially-approved", "approvedAmount": 80},
    )
    assert approved.status_code == 200
    first_remittance = client.patch(
        f"/api/v1/healthcare/insurance-claims/{claim['id']}",
        json={"status": "partially-paid", "paidAmount": 30},
    )
    assert first_remittance.status_code == 200
    final_remittance = client.patch(
        f"/api/v1/healthcare/insurance-claims/{claim['id']}",
        json={"status": "paid", "paidAmount": 80},
    )
    assert final_remittance.status_code == 200

    ledger = client.get("/api/v1/healthcare/treatment-ledger").json()
    insurer_payments = [entry for entry in ledger if entry["method"] == "insurance"]
    assert [entry["amount"] for entry in insurer_payments] == [50, 30]
    assert all(entry["chargeEntryId"] == charge["id"] for entry in insurer_payments)

    overpayment = client.patch(
        f"/api/v1/healthcare/insurance-claims/{claim['id']}",
        json={"status": "paid", "paidAmount": 81},
    )
    assert overpayment.status_code == 409
    exported = client.get("/api/v1/billing/accounting/insurance-claims.csv")
    assert exported.status_code == 200
    assert "CLM-1001" in exported.text

    unlinked_patient = client.post(
        "/api/v1/healthcare/patients",
        json={"fullName": "Unlinked Claim Patient"},
    ).json()
    unlinked_claim = client.post(
        "/api/v1/healthcare/insurance-claims",
        json={
            "patientId": unlinked_patient["id"],
            "payerName": ' =HYPERLINK("https://example.invalid","payer")',
            "billedAmount": 30,
            "currency": "INR",
        },
    ).json()
    safe_export = client.get("/api/v1/billing/accounting/insurance-claims.csv")
    assert "' =HYPERLINK" in safe_export.text
    client.patch(
        f"/api/v1/healthcare/insurance-claims/{unlinked_claim['id']}",
        json={"status": "submitted"},
    )
    client.patch(
        f"/api/v1/healthcare/insurance-claims/{unlinked_claim['id']}",
        json={"status": "approved", "approvedAmount": 30},
    )
    unlinked_paid = client.patch(
        f"/api/v1/healthcare/insurance-claims/{unlinked_claim['id']}",
        json={"status": "paid", "paidAmount": 30},
    )
    assert unlinked_paid.status_code == 200
    unlinked_remittance = next(
        entry
        for entry in client.get("/api/v1/healthcare/treatment-ledger").json()
        if entry["method"] == "insurance" and entry["patientId"] == unlinked_patient["id"]
    )
    assert unlinked_remittance["amount"] == 30
    assert unlinked_remittance["chargeEntryId"] is None


def test_pms_csv_reconciliation_reports_matches_and_missing_transactions(client):
    patient, charge = create_patient_charge(client, reference="invoice-200")
    payment_response = client.post(
        "/api/v1/healthcare/treatment-ledger",
        json={
            "patientId": patient["id"],
            "chargeEntryId": charge["id"],
            "entryType": "payment",
            "amount": 50,
            "currency": "INR",
            "method": "cash",
            "reference": "receipt-200",
        },
    )
    assert payment_response.status_code == 201
    csv_content = (
        "Transaction ID,Patient ID,Type,Amount,Currency\n"
        f"receipt-200,{patient['id']},payment,50.00,INR\n"
        f"unknown-transaction,{patient['id']},payment,10.00,INR\n"
        f"receipt-200,{patient['id']},payment,50.00,INR\n"
        f"invalid-transaction,{patient['id']},payment,0,INR\n"
    )
    reconciliation = client.post(
        "/api/v1/billing/pms/reconcile",
        files={"file": ("pms-transactions.csv", csv_content, "text/csv")},
    )
    assert reconciliation.status_code == 200
    counts = reconciliation.json()
    assert counts["matchedRows"] == 1
    assert counts["missingLocalRows"] == 1
    assert counts["missingPmsRows"] == 1
    assert counts["duplicateSourceRows"] == 1
    assert counts["invalidRows"] == 1

    rows = client.get(
        f"/api/v1/billing/pms/reconciliation-runs/{counts['id']}/rows"
    ).json()
    assert {row["status"] for row in rows} == {
        "matched",
        "missing-local",
        "missing-pms",
        "duplicate-source",
        "invalid-source",
    }
    exported_ledger = client.get("/api/v1/billing/accounting/ledger.csv")
    assert exported_ledger.status_code == 200
    assert "receipt-200" in exported_ledger.text


def test_crm_enquiry_conversion_and_patient_communication_history(client):
    invalid_enquiry = client.post(
        "/api/v1/healthcare/enquiries",
        json={"fullName": "No Contact"},
    )
    assert invalid_enquiry.status_code == 422

    enquiry_response = client.post(
        "/api/v1/healthcare/enquiries",
        json={
            "fullName": "Asha Rao",
            "email": "asha@example.com",
            "phone": "+91 9876543210",
            "source": "website",
            "requestedService": "Dental consultation",
            "notes": "Prefers morning appointments.",
        },
    )
    assert enquiry_response.status_code == 201
    enquiry = enquiry_response.json()
    assert enquiry["status"] == "new"

    contacted = client.patch(
        f"/api/v1/healthcare/enquiries/{enquiry['id']}",
        json={"status": "contacted"},
    )
    assert contacted.status_code == 200
    booked = client.patch(
        f"/api/v1/healthcare/enquiries/{enquiry['id']}",
        json={"status": "consultation-booked"},
    )
    assert booked.status_code == 200

    converted = client.post(f"/api/v1/healthcare/enquiries/{enquiry['id']}/convert")
    assert converted.status_code == 200
    assert converted.json()["status"] == "converted"
    patient_id = converted.json()["patientId"]
    patient = client.get("/api/v1/healthcare/patients").json()
    assert any(item["id"] == patient_id for item in patient)

    duplicate_conversion = client.post(
        f"/api/v1/healthcare/enquiries/{enquiry['id']}/convert"
    )
    assert duplicate_conversion.status_code == 409

    communication_response = client.post(
        f"/api/v1/healthcare/patients/{patient_id}/communications",
        json={
            "channel": "phone",
            "direction": "outbound",
            "summary": "Confirmed the consultation time.",
        },
    )
    assert communication_response.status_code == 201
    communication = communication_response.json()
    assert communication["actorId"]

    history = client.get(f"/api/v1/healthcare/patients/{patient_id}/communications")
    assert history.status_code == 200
    assert history.json()[0]["summary"] == "Confirmed the consultation time."


def test_manual_growth_listing_campaign_and_review_workflows(client):
    patient = client.post(
        "/api/v1/healthcare/patients",
        json={"fullName": "Growth Test Patient"},
    ).json()
    branch_id = patient["branchId"]

    listing = client.post(
        "/api/v1/growth/local-listings",
        json={
            "branchId": branch_id,
            "platform": "Google Business Profile",
            "profileUrl": "https://example.com/clinic",
            "primaryCategory": "Dentist",
            "nameMatches": True,
            "addressMatches": True,
            "phoneMatches": False,
            "notes": "Verify the listed phone number.",
        },
    )
    assert listing.status_code == 200
    listing_id = listing.json()["id"]
    assert listing.json()["lastReviewedAt"]

    updated_listing = client.post(
        "/api/v1/growth/local-listings",
        json={
            "branchId": branch_id,
            "platform": "Google Business Profile",
            "profileUrl": "https://example.com/clinic",
            "primaryCategory": "Dentist",
            "nameMatches": True,
            "addressMatches": True,
            "phoneMatches": True,
            "notes": "Phone number verified.",
        },
    )
    assert updated_listing.status_code == 200
    assert updated_listing.json()["id"] == listing_id
    assert updated_listing.json()["phoneMatches"] is True

    campaign = client.post(
        "/api/v1/growth/campaigns",
        json={
            "title": "Community check-up week",
            "channel": "community",
            "objective": "Promote preventative check-ups.",
            "status": "draft",
        },
    )
    assert campaign.status_code == 201
    campaign_id = campaign.json()["id"]
    assert client.patch(
        f"/api/v1/growth/campaigns/{campaign_id}",
        json={"status": "planned"},
    ).status_code == 200
    assert client.patch(
        f"/api/v1/growth/campaigns/{campaign_id}",
        json={"status": "completed"},
    ).status_code == 409

    review = client.post(
        "/api/v1/growth/reviews",
        json={
            "platform": "Google",
            "rating": 4,
            "reviewText": "The team explained the treatment clearly.",
            "branchId": branch_id,
        },
    )
    assert review.status_code == 201
    review_id = review.json()["id"]
    draft = client.patch(
        f"/api/v1/growth/reviews/{review_id}",
        json={"responseDraft": "Thank you for sharing your feedback."},
    )
    assert draft.status_code == 200
    assert draft.json()["responseStatus"] == "drafted"
    assert "publishedAt" not in draft.json()


def test_reminder_requires_confirmed_consent(client):
    patient_response = client.post(
        "/api/v1/healthcare/patients",
        json={"fullName": "Consent Test"},
    )
    patient = patient_response.json()
    response = client.post(
        "/api/v1/healthcare/reminders",
        json={
            "patientId": patient["id"],
            "reminderType": "hygiene",
            "message": "Book a cleaning",
            "channel": "sms",
            "scheduledAt": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "consentConfirmed": False,
        },
    )
    assert response.status_code == 400


def test_treatment_stage_transition_is_guarded(client):
    patient = client.post("/api/v1/healthcare/patients", json={"fullName": "Transition Patient"}).json()
    plan = client.post(
        "/api/v1/healthcare/treatment-plans",
        json={
            "patientId": patient["id"],
            "title": "Guarded transitions",
            "clinicianName": "Dr. Guard",
            "stages": [{"name": "Consultation", "status": "recommended"}],
        },
    ).json()
    stage_id = plan["stages"][0]["id"]
    invalid = client.patch(
        f"/api/v1/healthcare/treatment-stages/{stage_id}",
        json={"status": "completed"},
    )
    assert invalid.status_code == 409
    valid = client.patch(
        f"/api/v1/healthcare/treatment-stages/{stage_id}",
        json={"status": "accepted"},
    )
    assert valid.status_code == 200


def test_integration_configuration_never_persists_secret_fields(client):
    response = client.post(
        "/api/v1/healthcare/integrations",
        json={
            "provider": "Example PMS",
            "integrationType": "pms",
            "configurationJson": {
                "baseUrl": "https://example.invalid",
                "apiKey": "must-not-be-stored",
                "clientSecret": "must-not-be-stored",
            },
        },
    )
    assert response.status_code == 201
    config = response.json()["configurationJson"]
    assert config == {"baseUrl": "https://example.invalid"}


def test_csv_patient_import_maps_columns_and_exports_audited_data(client):
    response = client.post(
        "/api/v1/healthcare/integrations/csv/import",
        files={"file": ("patients.csv", "Patient Name,Email,Patient ID\nAsha Rao,asha@example.com,P-100\n", "text/csv")},
        data={"field_mapping": '{"fullName":"Patient Name","email":"Email","externalReference":"Patient ID"}'},
    )
    assert response.status_code == 201
    job = response.json()
    assert job["status"] == "completed"
    assert job["processedCount"] == 1
    assert job["failedCount"] == 0

    patients = client.get("/api/v1/healthcare/patients").json()
    assert any(patient["externalReference"] == "P-100" for patient in patients)

    export = client.get("/api/v1/healthcare/integrations/csv/export")
    assert export.status_code == 200
    assert "Asha Rao" in export.text
    jobs = client.get("/api/v1/healthcare/integrations/sync-jobs")
    assert jobs.status_code == 200
    assert jobs.json()[0]["id"] == job["id"]


def test_csv_patient_import_rejects_missing_mapped_columns(client):
    response = client.post(
        "/api/v1/healthcare/integrations/csv/import",
        files={"file": ("patients.csv", "Name\nAsha Rao\n", "text/csv")},
        data={"field_mapping": '{"fullName":"Patient Name"}'},
    )
    assert response.status_code == 400


def test_treatment_ledger_currency_and_visit_analytics(client):
    patient = client.post(
        "/api/v1/healthcare/patients",
        json={"fullName": "Ledger Patient"},
    ).json()
    patient_id = patient["id"]

    for entry_type, amount in (("charge", 10000), ("payment", 3500), ("refund", 500)):
        response = client.post(
            "/api/v1/healthcare/treatment-ledger",
            json={
                "patientId": patient_id,
                "entryType": entry_type,
                "amount": amount,
                "currency": "INR",
                "method": "card",
            },
        )
        assert response.status_code == 201

    mixed_currency = client.post(
        "/api/v1/healthcare/treatment-ledger",
        json={
            "patientId": patient_id,
            "entryType": "payment",
            "amount": 10,
            "currency": "USD",
        },
    )
    assert mixed_currency.status_code == 400

    recovery = client.get("/api/v1/healthcare/revenue-recovery").json()
    assert recovery["chargesValue"] == 10000
    assert recovery["paymentsReceived"] == 3500
    assert recovery["refundsValue"] == 500
    assert recovery["netCollected"] == 3000
    assert recovery["outstandingBalance"] == 7000

    completed_at = datetime.now(timezone.utc).isoformat()
    for _ in range(2):
        response = client.post(
            "/api/v1/healthcare/visits",
            json={
                "patientId": patient_id,
                "visitType": "consultation",
                "status": "completed",
                "completedAt": completed_at,
            },
        )
        assert response.status_code == 201

    analytics = client.get("/api/v1/healthcare/analytics").json()
    assert analytics["completedVisits"] == 2
    assert analytics["uniquePatientsSeen"] == 1
    assert analytics["returningPatients"] == 1
    assert analytics["patientRetentionRate"] == 100


def test_hygiene_recall_requires_approval_and_email_consent(client):
    patient = client.post(
        "/api/v1/healthcare/patients",
        json={"fullName": "Recall Patient", "email": "recall@example.com"},
    ).json()
    settings_response = client.put(
        "/api/v1/healthcare/recall-settings",
        json={
            "postProcedureDays": 2,
            "pendingTreatmentDays": 9,
            "hygieneRecallDays": 30,
        },
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["hygieneRecallDays"] == 30

    visit = client.post(
        "/api/v1/healthcare/visits",
        json={
            "patientId": patient["id"],
            "visitType": "hygiene",
            "status": "completed",
            "completedAt": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert visit.status_code == 201

    reminders = client.get("/api/v1/healthcare/reminders").json()
    assert len(reminders) == 1
    reminder = reminders[0]
    assert reminder["status"] == "pending-approval"
    assert reminder["channel"] == "email"
    scheduled_at = datetime.fromisoformat(reminder["scheduledAt"])
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    days_until_recall = (scheduled_at - datetime.now(timezone.utc)).total_seconds() / 86400
    assert 29.9 <= days_until_recall <= 30.1

    approval_url = f"/api/v1/healthcare/reminders/{reminder['id']}/approve"
    unconfirmed = client.post(approval_url, json={"consentConfirmed": False})
    assert unconfirmed.status_code == 400

    approved = client.post(approval_url, json={"consentConfirmed": True})
    assert approved.status_code == 200
    assert approved.json()["status"] == "scheduled"
    assert approved.json()["consentConfirmed"] is True

    outbox = client.get("/api/v1/healthcare/email-outbox")
    assert outbox.status_code == 200
    assert len(outbox.json()) == 1
    assert outbox.json()[0]["recipientEmail"] == "recall@example.com"
    assert outbox.json()[0]["status"] == "pending"


def test_treatment_recall_triggers_and_analytics_range_validation(client):
    patient = client.post(
        "/api/v1/healthcare/patients",
        json={"fullName": "Treatment Recall Patient", "email": "followup@example.com"},
    ).json()
    plan = client.post(
        "/api/v1/healthcare/treatment-plans",
        json={
            "patientId": patient["id"],
            "title": "Recall triggers",
            "clinicianName": "Dr. Test",
            "stages": [
                {"name": "Deferred stage", "status": "recommended"},
                {"name": "Completed stage", "status": "accepted"},
            ],
        },
    ).json()

    deferred = client.patch(
        f"/api/v1/healthcare/treatment-stages/{plan['stages'][0]['id']}",
        json={"status": "deferred", "reason": "Patient requested more time."},
    )
    completed = client.patch(
        f"/api/v1/healthcare/treatment-stages/{plan['stages'][1]['id']}",
        json={"status": "completed"},
    )
    assert deferred.status_code == 200
    assert completed.status_code == 200

    reminders = client.get("/api/v1/healthcare/reminders").json()
    assert {reminder["reminderType"] for reminder in reminders} == {
        "pending-visit",
        "post-procedure",
    }
    assert all(reminder["status"] == "pending-approval" for reminder in reminders)

    now = datetime.now(timezone.utc)
    invalid_range = client.get(
        "/api/v1/healthcare/analytics",
        params={
            "from_date": (now + timedelta(days=1)).isoformat(),
            "to_date": now.isoformat(),
        },
    )
    assert invalid_range.status_code == 400


def test_private_record_file_upload_and_download(client, monkeypatch):
    objects: dict[str, tuple[bytes, str]] = {}

    class MemoryDocumentStorage:
        def __init__(self):
            pass

        def put(self, key: str, content: bytes, content_type: str) -> None:
            objects[key] = (content, content_type)

        def get(self, key: str) -> StoredDocument:
            content, content_type = objects[key]
            return StoredDocument(content=content, content_type=content_type)

    monkeypatch.setattr(healthcare_router, "S3DocumentStorage", MemoryDocumentStorage)
    patient = client.post(
        "/api/v1/healthcare/patients",
        json={"fullName": "Document Patient"},
    ).json()
    record = client.post(
        "/api/v1/healthcare/records",
        json={
            "patientId": patient["id"],
            "recordType": "document",
            "title": "Referral",
            "sourceName": "Clinic",
            "metadataJson": {},
        },
    ).json()

    content = b"%PDF-1.4\n% test document\n"
    uploaded = client.post(
        f"/api/v1/healthcare/records/{record['id']}/file",
        files={"file": ("referral.pdf", content, "application/pdf")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["originalFilename"] == "referral.pdf"
    assert uploaded.json()["fileSizeBytes"] == len(content)
    assert uploaded.json()["versionNumber"] == 2

    downloaded = client.get(f"/api/v1/healthcare/records/{record['id']}/download")
    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert downloaded.headers["cache-control"] == "private, no-store"


def test_patient_portal_invitation_requires_activation_before_login(client):
    patient_response = client.post(
        "/api/v1/healthcare/patients",
        json={"fullName": "Portal Patient", "email": "portal@example.com"},
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    invitation = client.post(
        "/api/v1/patient-portal/invitations",
        json={"patientId": patient_id},
    )
    assert invitation.status_code == 201
    token = invitation.json()["invitationToken"]

    inactive_login = client.post(
        "/api/v1/patient-portal/login",
        json={"clinicId": client.get("/api/v1/clinic/profile").json()["id"], "email": "portal@example.com", "password": "LongTestPassword123"},
    )
    assert inactive_login.status_code == 401

    accepted = client.post(
        "/api/v1/patient-portal/invitations/accept",
        json={"invitationToken": token, "password": "LongTestPassword123"},
    )
    assert accepted.status_code == 204
    login = client.post(
        "/api/v1/patient-portal/login",
        json={"clinicId": client.get("/api/v1/clinic/profile").json()["id"], "email": "portal@example.com", "password": "LongTestPassword123"},
    )
    assert login.status_code == 200
    portal_token = login.json()["accessToken"]
    records = client.get(
        "/api/v1/patient-portal/records",
        headers={"Authorization": f"Bearer {portal_token}"},
    )
    assert records.status_code == 200


def test_first_branch_is_primary_and_staff_invitation_scopes_account(client):
    branch_response = client.post(
        "/api/v1/clinic/branches",
        json={"name": "North Clinic", "address": "10 Main Street", "phone": "+1-555-0100"},
    )
    assert branch_response.status_code == 201
    branch = branch_response.json()
    assert branch["isPrimary"] is True
    second_branch = client.post(
        "/api/v1/clinic/branches",
        json={"name": "Downtown Clinic"},
    ).json()

    invitation_response = client.post(
        "/api/v1/clinic/staff/invitations",
        json={
            "email": "newstaff@example.com",
            "fullName": "New Staff",
            "branchId": branch["id"],
        },
    )
    assert invitation_response.status_code == 201
    invitation_token = invitation_response.json()["invitationToken"]

    acceptance = client.post(
        "/api/v1/clinic/staff/invitations/accept",
        json={"invitationToken": invitation_token, "password": "LongStaffPassword123"},
    )
    assert acceptance.status_code == 204
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "newstaff@example.com", "password": "LongStaffPassword123"},
    )
    assert login.status_code == 200
    staff_branches = client.get(
        "/api/v1/clinic/branches",
        headers={"Authorization": f"Bearer {login.json()['accessToken']}"},
    )
    assert [item["id"] for item in staff_branches.json()] == [branch["id"]]
    assert second_branch["id"] != branch["id"]
