from app.models.user import User as UserModel
from app.schemas.user import User as UserSchema


def user_to_schema(user: UserModel) -> UserSchema:
    return UserSchema(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,  # type: ignore[arg-type]
        clinic_id=user.clinic_id,
        clinic_name=user.clinic.name,
        plan_tier=user.clinic.plan_tier,  # type: ignore[arg-type]
        created_at=user.created_at,
    )
