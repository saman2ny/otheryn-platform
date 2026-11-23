"""Expand healthcare, portal, integration, and clinic-operation capabilities.

Revision ID: f1a9c5e0d4b7
Revises: c7e4b2a91f22
Create Date: 2026-11-20
"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "f1a9c5e0d4b7"
down_revision: Union[str, Sequence[str], None] = "c7e4b2a91f22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clinics",
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "clinic_branches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinic_branches_clinic_id", "clinic_branches", ["clinic_id"])

    op.create_table(
        "staff_invitations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["clinic_branches.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_invitations_branch_id", "staff_invitations", ["branch_id"])
    op.create_index("ix_staff_invitations_clinic_id", "staff_invitations", ["clinic_id"])
    op.create_index("ix_staff_invitations_email", "staff_invitations", ["email"])
    op.create_index("ix_staff_invitations_token_hash", "staff_invitations", ["token_hash"], unique=True)

    connection = op.get_bind()
    clinic_ids = connection.execute(sa.text("SELECT id FROM clinics")).scalars().all()
    for clinic_id in clinic_ids:
        branch_id = str(uuid4())
        connection.execute(
            sa.text(
                "INSERT INTO clinic_branches "
                "(id, clinic_id, name, address, phone, is_primary) "
                "VALUES (:id, :clinic_id, :name, '', '', TRUE)"
            ),
            {"id": branch_id, "clinic_id": clinic_id, "name": "Main branch"},
        )

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("branch_id", sa.String(), nullable=True))
        batch.create_foreign_key(
            "fk_users_branch_id_clinic_branches",
            "clinic_branches",
            ["branch_id"],
            ["id"],
        )
    with op.batch_alter_table("patients") as batch:
        batch.add_column(sa.Column("branch_id", sa.String(), nullable=True))
        batch.create_foreign_key(
            "fk_patients_branch_id_clinic_branches",
            "clinic_branches",
            ["branch_id"],
            ["id"],
        )
    op.create_index("ix_users_branch_id", "users", ["branch_id"])
    op.create_index("ix_patients_branch_id", "patients", ["branch_id"])
    op.execute(
        sa.text(
            "UPDATE patients SET branch_id = "
            "(SELECT clinic_branches.id FROM clinic_branches "
            "WHERE clinic_branches.clinic_id = patients.clinic_id AND clinic_branches.is_primary = TRUE)"
        )
    )
    op.execute(
        sa.text(
            "UPDATE users SET branch_id = "
            "(SELECT clinic_branches.id FROM clinic_branches "
            "WHERE clinic_branches.clinic_id = users.clinic_id AND clinic_branches.is_primary = TRUE) "
            "WHERE users.clinic_id IS NOT NULL AND users.role = 'staff'"
        )
    )
    op.add_column(
        "health_records",
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "record_consents",
        sa.Column(
            "scope",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[\"view\"]'"),
        ),
    )
    op.create_table(
        "patient_record_shares",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("consent_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["consent_id"], ["record_consents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_record_shares_clinic_id", "patient_record_shares", ["clinic_id"])
    op.create_index("ix_patient_record_shares_consent_id", "patient_record_shares", ["consent_id"])
    op.create_index("ix_patient_record_shares_token_hash", "patient_record_shares", ["token_hash"], unique=True)
    op.add_column(
        "audit_events",
        sa.Column("actor_type", sa.String(), nullable=False, server_default="staff"),
    )
    with op.batch_alter_table("audit_events") as batch:
        batch.add_column(sa.Column("branch_id", sa.String(), nullable=True))
        batch.create_foreign_key(
            "fk_audit_events_branch_id_clinic_branches",
            "clinic_branches",
            ["branch_id"],
            ["id"],
        )
    op.create_index("ix_audit_events_branch_id", "audit_events", ["branch_id"])
    op.add_column(
        "integration_connections",
        sa.Column("last_error", sa.Text(), nullable=True),
    )

    op.create_table(
        "treatment_decisions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("stage_id", sa.String(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("actor_role", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["treatment_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treatment_decisions_clinic_id", "treatment_decisions", ["clinic_id"])
    op.create_index("ix_treatment_decisions_patient_id", "treatment_decisions", ["patient_id"])
    op.create_index("ix_treatment_decisions_stage_id", "treatment_decisions", ["stage_id"])
    op.create_index("ix_treatment_decisions_created_at", "treatment_decisions", ["created_at"])

    op.create_table(
        "health_record_revisions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("record_id", sa.String(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("correction_reason", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["record_id"], ["health_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id", "revision_number", name="uq_health_record_revision_number"),
    )
    op.create_index("ix_health_record_revisions_clinic_id", "health_record_revisions", ["clinic_id"])
    op.create_index("ix_health_record_revisions_record_id", "health_record_revisions", ["record_id"])

    op.create_table(
        "patient_portal_accounts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.Column("invitation_token_hash", sa.String(), nullable=True),
        sa.Column("invitation_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "email", name="uq_patient_portal_account_clinic_email"),
    )
    op.create_index("ix_patient_portal_accounts_clinic_id", "patient_portal_accounts", ["clinic_id"])
    op.create_index("ix_patient_portal_accounts_patient_id", "patient_portal_accounts", ["patient_id"], unique=True)
    op.create_index(
        "ix_patient_portal_accounts_invitation_token_hash",
        "patient_portal_accounts",
        ["invitation_token_hash"],
    )

    op.create_table(
        "integration_sync_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("connection_id", sa.String(), nullable=True),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("field_mapping", sa.JSON(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integration_sync_jobs_clinic_id", "integration_sync_jobs", ["clinic_id"])
    op.create_index("ix_integration_sync_jobs_connection_id", "integration_sync_jobs", ["connection_id"])


def downgrade() -> None:
    op.drop_index("ix_integration_sync_jobs_connection_id", table_name="integration_sync_jobs")
    op.drop_index("ix_integration_sync_jobs_clinic_id", table_name="integration_sync_jobs")
    op.drop_table("integration_sync_jobs")
    op.drop_index("ix_patient_record_shares_token_hash", table_name="patient_record_shares")
    op.drop_index("ix_patient_record_shares_consent_id", table_name="patient_record_shares")
    op.drop_index("ix_patient_record_shares_clinic_id", table_name="patient_record_shares")
    op.drop_table("patient_record_shares")
    op.drop_index(
        "ix_patient_portal_accounts_invitation_token_hash",
        table_name="patient_portal_accounts",
    )
    op.drop_index("ix_patient_portal_accounts_patient_id", table_name="patient_portal_accounts")
    op.drop_index("ix_patient_portal_accounts_clinic_id", table_name="patient_portal_accounts")
    op.drop_table("patient_portal_accounts")
    op.drop_index("ix_health_record_revisions_record_id", table_name="health_record_revisions")
    op.drop_index("ix_health_record_revisions_clinic_id", table_name="health_record_revisions")
    op.drop_table("health_record_revisions")
    op.drop_index("ix_treatment_decisions_created_at", table_name="treatment_decisions")
    op.drop_index("ix_treatment_decisions_stage_id", table_name="treatment_decisions")
    op.drop_index("ix_treatment_decisions_patient_id", table_name="treatment_decisions")
    op.drop_index("ix_treatment_decisions_clinic_id", table_name="treatment_decisions")
    op.drop_table("treatment_decisions")
    op.drop_column("integration_connections", "last_error")
    op.drop_index("ix_audit_events_branch_id", table_name="audit_events")
    with op.batch_alter_table("audit_events") as batch:
        batch.drop_constraint("fk_audit_events_branch_id_clinic_branches", type_="foreignkey")
        batch.drop_column("branch_id")
        batch.drop_column("actor_type")
    op.drop_column("record_consents", "scope")
    op.drop_column("health_records", "version_number")
    op.drop_index("ix_patients_branch_id", table_name="patients")
    op.drop_index("ix_users_branch_id", table_name="users")
    op.drop_index("ix_staff_invitations_token_hash", table_name="staff_invitations")
    op.drop_index("ix_staff_invitations_email", table_name="staff_invitations")
    op.drop_index("ix_staff_invitations_clinic_id", table_name="staff_invitations")
    op.drop_index("ix_staff_invitations_branch_id", table_name="staff_invitations")
    op.drop_table("staff_invitations")
    with op.batch_alter_table("patients") as batch:
        batch.drop_constraint("fk_patients_branch_id_clinic_branches", type_="foreignkey")
        batch.drop_column("branch_id")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("fk_users_branch_id_clinic_branches", type_="foreignkey")
        batch.drop_column("branch_id")
    op.drop_index("ix_clinic_branches_clinic_id", table_name="clinic_branches")
    op.drop_table("clinic_branches")
    op.drop_column("clinics", "onboarding_completed_at")
