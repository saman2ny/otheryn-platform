from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = "sqlite:///./dentalpilot.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    cors_origins: list[str] = ["http://localhost:4200"]
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-4-8"
    clinical_note_drafting_enabled: bool = False
    clinical_ai_data_processing_approved: bool = False

    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None
    razorpay_currency: str = "USD"
    razorpay_plan_ids: dict[str, dict[str, str]] = {}
    subscription_grace_period_days: int = Field(default=7, ge=1, le=30)
    billing_webhook_interval_seconds: int = Field(default=5, ge=1, le=60)
    billing_webhook_max_attempts: int = Field(default=10, ge=1, le=50)
    subscription_reconciliation_interval_seconds: int = Field(default=3600, ge=60)
    patient_payment_currency: str = "INR"

    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    aws_region: str = "us-east-1"
    s3_kms_key_id: str | None = None
    max_patient_document_bytes: int = 25_000_000

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender_email: str | None = None
    smtp_sender_name: str = "DentalPilot AI"
    smtp_use_ssl: bool = False
    smtp_use_starttls: bool = True
    email_worker_interval_seconds: int = 10
    email_max_attempts: int = 5

    # WhatsApp Cloud API
    whatsapp_phone_number_id: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_webhook_verify_token: str | None = None

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if bool(self.razorpay_key_id) != bool(self.razorpay_key_secret):
            raise ValueError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured together.")
        if self.clinical_note_drafting_enabled and not self.clinical_ai_data_processing_approved:
            raise ValueError(
                "Clinical note drafting requires an approved clinical-AI data-processing arrangement."
            )
        if self.app_environment == "production":
            if self.jwt_secret == "dev-secret-change-me" or len(self.jwt_secret) < 32:
                raise ValueError("Production requires a non-default JWT_SECRET of at least 32 characters.")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production requires a managed database; SQLite is not supported.")
            if "*" in self.cors_origins:
                raise ValueError("Production CORS origins must not include '*'.")
            if self.razorpay_key_id and not self.razorpay_webhook_secret:
                raise ValueError("Production Razorpay billing requires a webhook signing secret.")
            if self.razorpay_key_id:
                required = {"starter", "professional", "enterprise"}
                if not required.issubset(self.razorpay_plan_ids):
                    raise ValueError("Production Razorpay billing requires configured plan IDs for all paid tiers.")
                for tier in required:
                    if not {"monthly", "annual"}.issubset(self.razorpay_plan_ids[tier]):
                        raise ValueError(f"Production Razorpay billing is missing a billing-cycle plan for {tier}.")
        return self


settings = Settings()
