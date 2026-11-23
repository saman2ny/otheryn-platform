from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(
            "clinic_organizations.id",
            name="fk_clinics_organization_id",
            use_alter=True,
        ),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    specialty: Mapped[str] = mapped_column(String, default="general-dentistry")
    about_text: Mapped[str] = mapped_column(String, default="")
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, default="")
    address: Mapped[str] = mapped_column(String, default="")
    city: Mapped[str] = mapped_column(String, default="")
    country: Mapped[str] = mapped_column(String, default="")
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    brand_tone: Mapped[str] = mapped_column(String, default="friendly")
    target_audience: Mapped[str] = mapped_column(String, default="")
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan_tier: Mapped[str] = mapped_column(String, default="free")
    subscription_status: Mapped[str] = mapped_column(String, default="trialing")
    billing_cycle: Mapped[str] = mapped_column(String, default="monthly")
    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) + timedelta(days=30)
    )
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_credits_used: Mapped[int] = mapped_column(Integer, default=0)
    ai_credits_limit: Mapped[int] = mapped_column(Integer, default=20)
    clinical_note_drafting_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    users: Mapped[list["User"]] = relationship(back_populates="clinic")  # noqa: F821
