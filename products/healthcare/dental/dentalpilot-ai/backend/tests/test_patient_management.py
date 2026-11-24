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