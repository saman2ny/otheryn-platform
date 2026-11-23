"""Persist recurring SaaS billing lifecycle and gated clinical note drafting.

Revision ID: c4a2d9e7f631
Revises: a6c91f20d473
Create Date: 2026-11-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4a2d9e7f631"
down_revision: Union[str, Sequence[str], None] = "a6c91f20d473"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("clinics") as batch_op:
        batch_op.add_column(sa.Column("grace_period_ends_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "clinical_note_drafting_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )

    with op.batch_alter_table("clinical_note_drafts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "generation_source",
                sa.String(),
                nullable=False,
                server_default="clinician",
            )
        )

    with op.batch_alter_table("invoices") as batch_op:
        batch_op.add_column(sa.Column("external_invoice_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("razorpay_subscription_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("razorpay_payment_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("period_start", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("period_end", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_unique_constraint("uq_invoices_external_invoice_id", ["external_invoice_id"])
        batch_op.create_unique_constraint("uq_invoices_razorpay_payment_id", ["razorpay_payment_id"])
        batch_op.create_index("ix_invoices_razorpay_subscription_id", ["razorpay_subscription_id"])

    op.create_table(
        "clinic_subscriptions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("razorpay_subscription_id", sa.String(), nullable=True),
        sa.Column("razorpay_plan_id", sa.String(), nullable=False),
        sa.Column("plan_tier", sa.String(), nullable=False),
        sa.Column("billing_cycle", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("cancel_at_cycle_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_period_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("checkout_signature_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("short_url", sa.String(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinic_subscriptions_clinic_id", "clinic_subscriptions", ["clinic_id"])
    op.create_index("ix_clinic_subscriptions_status", "clinic_subscriptions", ["status"])
    op.create_index(
        "ix_clinic_subscriptions_razorpay_subscription_id",
        "clinic_subscriptions",
        ["razorpay_subscription_id"],
        unique=True,
    )
    op.create_index(
        "uq_clinic_subscription_current",
        "clinic_subscriptions",
        ["clinic_id"],
        unique=True,
        sqlite_where=sa.text("is_current = 1"),
        postgresql_where=sa.text("is_current = true"),
    )

    op.create_table(
        "billing_webhook_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider_event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("razorpay_subscription_id", sa.String(), nullable=True),
        sa.Column("razorpay_invoice_id", sa.String(), nullable=True),
        sa.Column("razorpay_payment_id", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("processing_status", sa.String(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_event_id", name="uq_billing_webhook_event_provider_id"),
    )
    op.create_index("ix_billing_webhook_events_event_type", "billing_webhook_events", ["event_type"])
    op.create_index("ix_billing_webhook_events_subscription_id", "billing_webhook_events", ["razorpay_subscription_id"])
    op.create_index("ix_billing_webhook_events_processing_status", "billing_webhook_events", ["processing_status"])
    op.create_index("ix_billing_webhook_events_available_at", "billing_webhook_events", ["available_at"])
    op.create_index(
        "ix_billing_webhook_events_ready",
        "billing_webhook_events",
        ["processing_status", "available_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_billing_webhook_events_ready", table_name="billing_webhook_events")
    op.drop_index("ix_billing_webhook_events_available_at", table_name="billing_webhook_events")
    op.drop_index("ix_billing_webhook_events_processing_status", table_name="billing_webhook_events")
    op.drop_index("ix_billing_webhook_events_subscription_id", table_name="billing_webhook_events")
    op.drop_index("ix_billing_webhook_events_event_type", table_name="billing_webhook_events")
    op.drop_table("billing_webhook_events")

    op.drop_index("uq_clinic_subscription_current", table_name="clinic_subscriptions")
    op.drop_index("ix_clinic_subscriptions_razorpay_subscription_id", table_name="clinic_subscriptions")
    op.drop_index("ix_clinic_subscriptions_status", table_name="clinic_subscriptions")
    op.drop_index("ix_clinic_subscriptions_clinic_id", table_name="clinic_subscriptions")
    op.drop_table("clinic_subscriptions")

    with op.batch_alter_table("invoices") as batch_op:
        batch_op.drop_index("ix_invoices_razorpay_subscription_id")
        batch_op.drop_constraint("uq_invoices_razorpay_payment_id", type_="unique")
        batch_op.drop_constraint("uq_invoices_external_invoice_id", type_="unique")
        batch_op.drop_column("paid_at")
        batch_op.drop_column("period_end")
        batch_op.drop_column("period_start")
        batch_op.drop_column("razorpay_payment_id")
        batch_op.drop_column("razorpay_subscription_id")
        batch_op.drop_column("external_invoice_id")

    with op.batch_alter_table("clinical_note_drafts") as batch_op:
        batch_op.drop_column("generation_source")

    with op.batch_alter_table("clinics") as batch_op:
        batch_op.drop_column("clinical_note_drafting_enabled")
        batch_op.drop_column("grace_period_ends_at")
