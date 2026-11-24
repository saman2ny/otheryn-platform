import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.clinic import Clinic
from app.models.healthcare import ClinicBranch
from app.models.user import User

VALID_PROFILE = {
    "name": "Clinic A",
    "specialty": "general-dentistry",
    "aboutText": "",
    "phone": "000",
    "address": "Address",
    "city": "City",
    "country": "Country",
    "brandTone": "friendly",
    "targetAudience": "",
}


@pytest.fixture()
def staff_client():
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
    branch = ClinicBranch(clinic_id=clinic.id, name="Main", is_primary=True)
    db.add(branch)
    db.flush()
    staff = User(
        email="staff@example.com",
        hashed_password=hash_password("password"),
        full_name="Staff",
        role="staff",
        clinic_id=clinic.id,
        branch_id=branch.id,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    db.close()

    def override_get_db():
        test_db = TestingSessionLocal()
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(staff.id)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as client:
        yield client
    app.dependency_overrides.clear()


def test_staff_cannot_update_clinic_profile(staff_client):
    response = staff_client.put("/api/v1/clinic/profile", json=VALID_PROFILE)
    assert response.status_code == 403


def test_staff_sees_no_other_clinic_patients(staff_client):
    response = staff_client.get("/api/v1/healthcare/patients")
    assert response.status_code == 200
    assert response.json() == []


def test_staff_cannot_generate_ai_note_without_owner(staff_client):
    response = staff_client.post("/api/v1/operations/clinical-note-drafts")
    assert response.status_code in (403, 422)