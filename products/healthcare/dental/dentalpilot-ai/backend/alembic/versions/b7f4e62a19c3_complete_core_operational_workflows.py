"""Add core finance, patient visits, file metadata, and recall delivery state.

Revision ID: b7f4e62a19c3
Revises: e118a37c2f64
Create Date: 2026-11-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7f4e62a19c3"
down_revision: Union[str, Sequence[str], None] = "e118a37c2f64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("health_records", sa.Column("storage_key", sa.String(), nullable=True))
    op.add_column("health_records", sa.Column("original_filename", sa.String(), nullable=True))
    op.add_column("health_records", sa.Column("mime_type", sa.String(), nullable=True))
    op.add_column("health_records", sa.Column("file_size_bytes", sa.Integer(), nullable=True))
    op.add_column("health_records", sa.Column("file_sha256", sa.String(length=64), nullable=True))
    op.add_column("recall_reminders", sa.Column("consent_confirmed_by", sa.String(), nullable=True))
    op.add_column(
        "recall_reminders",
        sa.Column("consent_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("recall_reminders", sa.Column("trigger_key", sa.String(), nullable=True))
    op.create_index(
        "uq_recall_reminders_trigger_key",
        "recall_reminders",
        ["trigger_key"],
        unique=True,
    )

    op.create_table(
        "patient_visits",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=True),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("visit_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["clinic_branches.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_visits_clinic_id", "patient_visits", ["clinic_id"])
    op.create_index("ix_patient_visits_branch_id", "patient_visits", ["branch_id"])
    op.create_index("ix_patient_visits_patient_id", "patient_visits", ["patient_id"])

    op.create_table(
        "treatment_ledger_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=True),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("stage_id", sa.String(), nullable=True),
        sa.Column("entry_type", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["clinic_branches.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["treatment_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treatment_ledger_entries_clinic_id", "treatment_ledger_entries", ["clinic_id"])
    op.create_index("ix_treatment_ledger_entries_branch_id", "treatment_ledger_entries", ["branch_id"])
    op.create_index("ix_treatment_ledger_entries_patient_id", "treatment_ledger_entries", ["patient_id"])
    op.create_index("ix_treatment_ledger_entries_stage_id", "treatment_ledger_entries", ["stage_id"])
    op.create_index("ix_treatment_ledger_entries_created_at", "treatment_ledger_entries", ["created_at"])

    op.create_table(
        "recall_automation_settings",
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("post_procedure_days", sa.Integer(), nullable=False),
        sa.Column("pending_treatment_days", sa.Integer(), nullable=False),
        sa.Column("hygiene_recall_days", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("clinic_id"),
    )

    op.create_table(
        "email_outbox",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("reminder_id", sa.String(), nullable=True),
        sa.Column("recipient_email", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["reminder_id"], ["recall_reminders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reminder_id", name="uq_email_outbox_reminder_id"),
    )
    op.create_index("ix_email_outbox_clinic_id", "email_outbox", ["clinic_id"])
    op.create_index("ix_email_outbox_patient_id", "email_outbox", ["patient_id"])
    op.create_index("ix_email_outbox_status", "email_outbox", ["status"])
    op.create_index("ix_email_outbox_available_at", "email_outbox", ["available_at"])


def downgrade() -> None:
    op.drop_index("ix_email_outbox_available_at", table_name="email_outbox")
    op.drop_index("ix_email_outbox_status", table_name="email_outbox")
    op.drop_index("ix_email_outbox_patient_id", table_name="email_outbox")
    op.drop_index("ix_email_outbox_clinic_id", table_name="email_outbox")
    op.drop_table("email_outbox")
    op.drop_table("recall_automation_settings")
    op.drop_index("ix_treatment_ledger_entries_created_at", table_name="treatment_ledger_entries")
    op.drop_index("ix_treatment_ledger_entries_stage_id", table_name="treatment_ledger_entries")
    op.drop_index("ix_treatment_ledger_entries_patient_id", table_name="treatment_ledger_entries")
    op.drop_index("ix_treatment_ledger_entries_branch_id", table_name="treatment_ledger_entries")
    op.drop_index("ix_treatment_ledger_entries_clinic_id", table_name="treatment_ledger_entries")
    op.drop_table("treatment_ledger_entries")
    op.drop_index("ix_patient_visits_patient_id", table_name="patient_visits")
    op.drop_index("ix_patient_visits_branch_id", table_name="patient_visits")
    op.drop_index("ix_patient_visits_clinic_id", table_name="patient_visits")
    op.drop_table("patient_visits")
    op.drop_index("uq_recall_reminders_trigger_key", table_name="recall_reminders")
    op.drop_column("recall_reminders", "trigger_key")
    op.drop_column("recall_reminders", "consent_confirmed_at")
    op.drop_column("recall_reminders", "consent_confirmed_by")
    op.drop_column("health_records", "file_sha256")
    op.drop_column("health_records", "file_size_bytes")
    op.drop_column("health_records", "mime_type")
    op.drop_column("health_records", "original_filename")
    op.drop_column("health_records", "storage_key")
