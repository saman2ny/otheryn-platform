from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.healthcare import PatientPortalAccount
from app.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise unauthorized from None

    if payload.get("type") != "access":
        raise unauthorized

    user = db.get(User, payload.get("sub"))
    if user is None:
        raise unauthorized
    if user.role == "staff" and user.clinic_id is not None and user.branch_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinic staff account must be assigned to a branch.",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def get_current_patient(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> PatientPortalAccount:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate patient credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise unauthorized from None

    if payload.get("type") != "patient_access":
        raise unauthorized

    account = db.get(PatientPortalAccount, payload.get("sub"))
    if account is None or account.hashed_password is None or account.email_verified_at is None:
        raise unauthorized
    return account


CurrentPatient = Annotated[PatientPortalAccount, Depends(get_current_patient)]


def require_owner(current_user: CurrentUser) -> User:
    """Owner or super_admin — for actions scoped to running a clinic (billing, profile)."""
    if current_user.role not in ("owner", "super_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a clinic owner can do this.")
    return current_user


def require_super_admin(current_user: CurrentUser) -> User:
    """Platform-level access only — not scoped to any single clinic."""
    if current_user.role != "super_admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Super admin access required.")
    return current_user


RequireOwner = Annotated[User, Depends(require_owner)]
RequireSuperAdmin = Annotated[User, Depends(require_super_admin)]
