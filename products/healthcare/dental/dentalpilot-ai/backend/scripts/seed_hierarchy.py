"""Seed one demo clinic with a login at each level of the role hierarchy.

Usage:
    cd backend && source .venv/bin/activate && python scripts/seed_hierarchy.py

Bypasses the normal /auth/register endpoint (which creates a new clinic per user)
to seed three users sharing one clinic. Safe to re-run: skips accounts that
already exist and assigns legacy demo staff to the clinic's primary branch.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.clinic import Clinic  # noqa: E402
from app.models.healthcare import ClinicBranch  # noqa: E402
from app.models.user import User  # noqa: E402

PASSWORD = "password123"

ACCOUNTS = [
    {"role": "super_admin", "email": "super-admin@dentalpilot.ai", "full_name": "Platform Super Admin"},
    {"role": "owner", "email": "owner@brightsmiledental.io", "full_name": "Dr. Owner Demo"},
    {"role": "staff", "email": "staff@brightsmiledental.io", "full_name": "Staff Demo"},
]


def main() -> None:
    db = SessionLocal()
    try:
        clinic = db.query(Clinic).filter(Clinic.name == "Bright Smile Dental (Demo)").first()
        if clinic is None:
            clinic = Clinic(name="Bright Smile Dental (Demo)")
            db.add(clinic)
            db.flush()
            print(f"Created clinic: {clinic.name} ({clinic.id})")
        else:
            print(f"Using existing clinic: {clinic.name} ({clinic.id})")

        branch = (
            db.query(ClinicBranch)
            .filter(ClinicBranch.clinic_id == clinic.id, ClinicBranch.is_primary.is_(True))
            .first()
        )
        if branch is None:
            branch = ClinicBranch(clinic_id=clinic.id, name="Main branch", is_primary=True)
            db.add(branch)
            db.flush()

        for account in ACCOUNTS:
            existing = db.query(User).filter(User.email == account["email"]).first()
            if existing is not None:
                if existing.role == "staff" and existing.branch_id is None:
                    existing.branch_id = branch.id
                print(f"  skip (already exists): {account['role']:<12} {account['email']}")
                continue

            user = User(
                email=account["email"],
                hashed_password=hash_password(PASSWORD),
                full_name=account["full_name"],
                role=account["role"],
                clinic_id=clinic.id,
                branch_id=branch.id if account["role"] == "staff" else None,
            )
            db.add(user)
            print(f"  created: {account['role']:<12} {account['email']}")

        db.commit()
    finally:
        db.close()

    print("\nLogin credentials (password is the same for all three):")
    print(f"  password: {PASSWORD}\n")
    for account in ACCOUNTS:
        print(f"  {account['role']:<12} {account['email']}")


if __name__ == "__main__":
    main()
