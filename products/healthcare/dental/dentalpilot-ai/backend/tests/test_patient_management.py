import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.clinic import Clinic
from app.models.user import User
from app.models.user import User


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
    clinic = Clinic(name="Clinic A", plan_tier="free")
    db.add(clinic)
    db.flush()
    owner = User(
        email="owner@example.com",
        hashed_password=hash_password("password"),
        full_name="Owner",
        role="owner",
        clinic_id=clinic.id,
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)
    db.close()

    def override_get_db():
        test_db = TestingSessionLocal()
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(owner.id)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as c:
        yield c
    app.dependency_overrides.clear()


def _create_patient(client, **overrides):
    payload = {
        "fullName": "Test Patient",
        "email": "patient@example.com",
        "phone": "555-0100",
        "consentChannel": "email",
    }
    payload.update(overrides)
    response = client.post("/api/v1/healthcare/patients", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_get_patient(client):
    patient = _create_patient(client)
    response = client.get(f"/api/v1/healthcare/patients/{patient['id']}")
    assert response.status_code == 200
    assert response.json()["fullName"] == "Test Patient"


def test_update_patient_partial(client):
    patient = _create_patient(client)
    response = client.patch(
        f"/api/v1/healthcare/patients/{patient['id']}",
        json={"phone": "555-0199"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == "555-0199"
    assert body["fullName"] == "Test Patient"


def test_update_patient_invalid(client):
    patient = _create_patient(client)
    response = client.patch(
        f"/api/v1/healthcare/patients/{patient['id']}",
        json={"fullName": ""},
    )
    assert response.status_code == 422


def test_medical_history_roundtrip(client):
    patient = _create_patient(client)
    history = {
        "conditions": ["Hypertension"],
        "allergies": ["Penicillin"],
        "medications": ["Amlodipine"],
        "surgeries": [],
        "notes": "Patient-reported.",
    }
    response = client.patch(
        f"/api/v1/healthcare/patients/{patient['id']}",
        json={"medicalHistory": history},
    )
    assert response.status_code == 200
    fetched = client.get(f"/api/v1/healthcare/patients/{patient['id']}").json()
    assert fetched["medicalHistory"]["conditions"] == ["Hypertension"]


def test_dental_history_roundtrip(client):
    patient = _create_patient(client)
    history = {
        "previousTreatments": ["Root canal"],
        "conditions": ["Sensitivity"],
        "procedures": ["Crown"],
        "concerns": "Patient reports sensitivity.",
    }
    response = client.patch(
        f"/api/v1/healthcare/patients/{patient['id']}",
        json={"dentalHistory": history},
    )
    assert response.status_code == 200
    fetched = client.get(f"/api/v1/healthcare/patients/{patient['id']}").json()
    assert fetched["dentalHistory"]["previousTreatments"] == ["Root canal"]


def test_emergency_contacts_roundtrip(client):
    patient = _create_patient(client)
    contacts = [
        {"name": "Jane Doe", "relationship": "Spouse", "phone": "555-0101"},
    ]
    response = client.patch(
        f"/api/v1/healthcare/patients/{patient['id']}",
        json={"emergencyContacts": contacts},
    )
    assert response.status_code == 200
    fetched = client.get(f"/api/v1/healthcare/patients/{patient['id']}").json()
    assert fetched["emergencyContacts"][0]["name"] == "Jane Doe"


def test_duplicate_detection(client):
    _create_patient(client, email="dup@example.com", phone="555-0200")
    matches = client.get(
        "/api/v1/healthcare/patients/duplicates",
        params={"email": "dup@example.com"},
    )
    assert matches.status_code == 200
    assert len(matches.json()) == 1
    assert matches.json()[0]["matchedOn"] == "email"


def test_cross_clinic_access_denied(client):
    patient = _create_patient(client)
    register = client.post(
        "/api/v1/auth/register",
        json={
            "clinicName": "Clinic B",
            "fullName": "Dr. B",
            "email": "b@example.com",
            "password": "password123",
        },
    )
    assert register.status_code == 200
    token_b = register.json()["accessToken"]
    with TestClient(app, headers={"Authorization": f"Bearer {token_b}"}) as client_b:
        assert client_b.get(f"/api/v1/healthcare/patients/{patient['id']}").status_code == 404
        assert (
            client_b.patch(
                f"/api/v1/healthcare/patients/{patient['id']}",
                json={"phone": "000"},
            ).status_code
            == 404
        )


def test_patient_revisions(client):
    patient = _create_patient(client)
    client.patch(f"/api/v1/healthcare/patients/{patient['id']}", json={"phone": "1"})
    client.patch(f"/api/v1/healthcare/patients/{patient['id']}", json={"phone": "2"})
    revisions = client.get(f"/api/v1/healthcare/patients/{patient['id']}/revisions")
    assert revisions.status_code == 200
    assert len(revisions.json()) == 2


def _portal_token(client, patient):
    me = client.get("/api/v1/auth/me").json()
    clinic_id = me["clinicId"]
    invite = client.post(
        "/api/v1/patient-portal/invitations",
        json={"patientId": patient["id"]},
    )
    assert invite.status_code == 201
    accept = client.post(
        "/api/v1/patient-portal/invitations/accept",
        json={"invitationToken": invite.json()["invitationToken"], "password": "password1234"},
    )
    assert accept.status_code == 204
    login = client.post(
        "/api/v1/patient-portal/login",
        json={"clinicId": clinic_id, "email": patient["email"], "password": "password1234"},
    )
    assert login.status_code == 200
    return login.json()["accessToken"]


def test_patient_search_and_pagination(client):
    _create_patient(client, fullName="Alice Smith", email="alice@example.com")
    _create_patient(client, fullName="Bob Jones", email="bob@example.com")

    search = client.get("/api/v1/healthcare/patients", params={"q": "Alice"})
    assert search.status_code == 200
    assert len(search.json()) == 1

    paged = client.get("/api/v1/healthcare/patients", params={"limit": 1, "offset": 0})
    assert paged.status_code == 200
    assert len(paged.json()) == 1


def test_patient_portal_medical_history(client):
    patient = _create_patient(client, email="portal@example.com")
    client.patch(
        f"/api/v1/healthcare/patients/{patient['id']}",
        json={"medicalHistory": {"conditions": ["Asthma"], "allergies": ["Penicillin"]}},
    )
    token = _portal_token(client, patient)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as portal:
        response = portal.get("/api/v1/patient-portal/medical-history")
        assert response.status_code == 200
        assert response.json()["conditions"] == ["Asthma"]


def test_patient_portal_dental_history(client):
    patient = _create_patient(client, email="portal-dental@example.com")
    client.patch(
        f"/api/v1/healthcare/patients/{patient['id']}",
        json={"dentalHistory": {"previousTreatments": ["Root canal"]}},
    )
    token = _portal_token(client, patient)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as portal:
        response = portal.get("/api/v1/patient-portal/dental-history")
        assert response.status_code == 200
        assert response.json()["previousTreatments"] == ["Root canal"]


def test_patient_portal_emergency_contacts(client):
    patient = _create_patient(client, email="portal-ec@example.com")
    client.patch(
        f"/api/v1/healthcare/patients/{patient['id']}",
        json={"emergencyContacts": [{"name": "Jane", "relationship": "Spouse", "phone": "555"}]},
    )
    token = _portal_token(client, patient)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as portal:
        response = portal.get("/api/v1/patient-portal/emergency-contacts")
        assert response.status_code == 200
        assert response.json()[0]["name"] == "Jane"


def test_patient_portal_cannot_read_another_patient(client):
    patient_a = _create_patient(client, email="portal-a@example.com")
    _create_patient(client, email="portal-b@example.com")
    token_a = _portal_token(client, patient_a)
    with TestClient(app, headers={"Authorization": f"Bearer {token_a}"}) as portal:
        response = portal.get("/api/v1/patient-portal/medical-history")
        assert response.status_code == 200
        assert response.json() == {}


def test_duplicate_patient_blocked(client):
    _create_patient(client, fullName="Duplicate Person", email="dup@example.com")
    response = client.post(
        "/api/v1/healthcare/patients",
        json={"fullName": "Duplicate Person", "email": "dup@example.com", "consentChannel": "email"},
    )
    assert response.status_code == 409


def test_medical_history_partial_merge(client):
    patient = _create_patient(client)
    client.patch(
        f"/api/v1/healthcare/patients/{patient['id']}",
        json={"medicalHistory": {"conditions": ["Asthma"], "allergies": ["Penicillin"]}},
    )
    client.patch(
        f"/api/v1/healthcare/patients/{patient['id']}",
        json={"medicalHistory": {"medications": ["Amlodipine"]}},
    )
    fetched = client.get(f"/api/v1/healthcare/patients/{patient['id']}").json()
    assert fetched["medicalHistory"]["conditions"] == ["Asthma"]
    assert fetched["medicalHistory"]["allergies"] == ["Penicillin"]
    assert fetched["medicalHistory"]["medications"] == ["Amlodipine"]


def test_super_admin_can_list_all_clinics(client):
    _create_patient(client, fullName="Clinic A Patient", email="a-patient@example.com")
    register = client.post(
        "/api/v1/auth/register",
        json={
            "clinicName": "Clinic B",
            "fullName": "Dr. B",
            "email": "clinic-b-owner@example.com",
            "password": "password123",
        },
    )
    assert register.status_code == 200
    token_b = register.json()["accessToken"]
    with TestClient(app, headers={"Authorization": f"Bearer {token_b}"}) as client_b:
        created = client_b.post(
            "/api/v1/healthcare/patients",
            json={
                "fullName": "Clinic B Patient",
                "email": "b-patient@example.com",
                "consentChannel": "email",
            },
        )
        assert created.status_code == 201

    # Promote the existing owner to super_admin directly in the test DB.
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    db.query(User).filter(User.email == "owner@example.com").update({"role": "super_admin"})
    db.commit()
    gen.close()

    response = client.get("/api/v1/healthcare/patients")
    assert response.status_code == 200
    assert len(response.json()) >= 2