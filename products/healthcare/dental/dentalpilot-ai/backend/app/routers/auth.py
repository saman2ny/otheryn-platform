import jwt
from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.clinic import Clinic
from app.models.healthcare import ClinicBranch
from app.models.user import User
from app.schemas.common import CamelModel
from app.schemas.user import AuthResponse, AuthTokens, ForgotPasswordRequest, LoginRequest, RegisterRequest
from app.schemas.user import User as UserSchema
from app.services.mappers import user_to_schema

router = APIRouter(prefix="/auth", tags=["auth"])


class RefreshRequest(CamelModel):
    refresh_token: str


def _issue_tokens(user_id: str) -> AuthTokens:
    return AuthTokens(access_token=create_access_token(user_id), refresh_token=create_refresh_token(user_id))


@router.post("/register", response_model=AuthResponse)
def register(request: RegisterRequest, db: DbSession) -> AuthResponse:
    if db.query(User).filter(User.email == request.email).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

    clinic = Clinic(name=request.clinic_name)
    db.add(clinic)
    db.flush()

    db.add(ClinicBranch(clinic_id=clinic.id, name="Main branch", is_primary=True))
    db.flush()

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role="owner",  # registering creates a new clinic, so this user owns it
        clinic_id=clinic.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    tokens = _issue_tokens(user.id)
    return AuthResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token, user=user_to_schema(user))


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest, db: DbSession) -> AuthResponse:
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    user = db.query(User).filter(User.email == request.email).first()
    if user is None or not verify_password(request.password, user.hashed_password):
        raise invalid

    tokens = _issue_tokens(user.id)
    return AuthResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token, user=user_to_schema(user))


@router.post("/refresh", response_model=AuthTokens)
def refresh(request: RefreshRequest, db: DbSession) -> AuthTokens:
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token.")
    try:
        payload = decode_token(request.refresh_token)
    except jwt.PyJWTError:
        raise invalid from None

    if payload.get("type") != "refresh":
        raise invalid

    user = db.get(User, payload.get("sub"))
    if user is None:
        raise invalid

    return _issue_tokens(user.id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    """Stateless JWT logout — the client discards its tokens; nothing to invalidate server-side."""
    return None


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(request: ForgotPasswordRequest, db: DbSession) -> None:
    # Always return 204 regardless of whether the email exists, to avoid leaking account existence.
    db.query(User).filter(User.email == request.email).first()
    return None


@router.get("/me", response_model=UserSchema)
def me(current_user: CurrentUser) -> UserSchema:
    return user_to_schema(current_user)
