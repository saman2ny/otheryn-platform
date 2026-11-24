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


def test_auth_me_returns_current_user(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "owner@example.com"


def test_register_login_and_me(client):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "clinicName": "New Clinic",
            "fullName": "Dr. New",
            "email": "new-clinic@example.com",
            "password": "password123",
        },
    )
    assert register.status_code == 200
    body = register.json()
    assert body["user"]["email"] == "new-clinic@example.com"
    assert body["accessToken"]
    assert body["refreshToken"]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "new-clinic@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["accessToken"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new-clinic@example.com"


def test_login_rejects_invalid_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_refresh_rejects_access_token(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "password"},
    )
    assert login.status_code == 200

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": login.json()["accessToken"]},
    )

    assert response.status_code == 401


def test_tenant_isolation_between_clinics(client):
    patient = client.post(
        "/api/v1/healthcare/patients",
        json={
            "fullName": "Patient A",
            "email": "patient-a@example.com",
            "consentChannel": "email",
        },
    )
    assert patient.status_code == 201
    patient_id = patient.json()["id"]

    own_list = client.get("/api/v1/healthcare/patients")
    assert own_list.status_code == 200
    assert any(p["id"] == patient_id for p in own_list.json())

    register = client.post(
        "/api/v1/auth/register",
        json={
            "clinicName": "Clinic B",
            "fullName": "Dr. B",
            "email": "clinic-b@example.com",
            "password": "password123",
        },
    )
    assert register.status_code == 200
    token_b = register.json()["accessToken"]

    with TestClient(app, headers={"Authorization": f"Bearer {token_b}"}) as client_b:
        other_list = client_b.get("/api/v1/healthcare/patients")
        assert other_list.status_code == 200
        assert other_list.json() == []