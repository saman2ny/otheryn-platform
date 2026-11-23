"""Add native dental operations and multi-clinic organizations.

Revision ID: a6c91f20d473
Revises: 9e3f6a4b2c10
Create Date: 2026-11-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6c91f20d473"
down_revision: Union[str, Sequence[str], None] = "9e3f6a4b2c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinic_organizations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinic_organizations_owner_user_id", "clinic_organizations", ["owner_user_id"])
    op.create_table(
        "organization_members",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["clinic_organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_member_user"),
    )
    for column in ("organization_id", "user_id", "clinic_id"):
        op.create_index(f"ix_organization_members_{column}", "organization_members", [column])
    op.create_table(
        "organization_invitations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("invited_by", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["accepted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["clinic_organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "email", name="uq_organization_invitation_email"),
        sa.UniqueConstraint("token_hash"),
    )
    for column in ("organization_id", "email"):
        op.create_index(f"ix_organization_invitations_{column}", "organization_invitations", [column])

    with op.batch_alter_table("clinics") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_clinics_organization_id",
            "clinic_organizations",
            ["organization_id"],
            ["id"],
        )
        batch_op.create_index("ix_clinics_organization_id", ["organization_id"])

    op.create_table(
        "dental_workflow_cases",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=True),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("treatment_stage_id", sa.String(), nullable=True),
        sa.Column("case_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("provider_name", sa.String(), nullable=False),
        sa.Column("external_reference", sa.String(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["clinic_branches.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["treatment_stage_id"], ["treatment_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("clinic_id", "branch_id", "patient_id", "status"):
        op.create_index(f"ix_dental_workflow_cases_{column}", "dental_workflow_cases", [column])
    op.create_index(
        "ix_dental_workflow_cases_clinic_type_status",
        "dental_workflow_cases",
        ["clinic_id", "case_type", "status"],
    )
    op.create_table(
        "dental_workflow_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["case_id"], ["dental_workflow_cases.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("clinic_id", "case_id"):
        op.create_index(f"ix_dental_workflow_events_{column}", "dental_workflow_events", [column])

    op.create_table(
        "clinic_assets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
        sa.Column("asset_tag", sa.String(), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("serial_number", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("next_service_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["clinic_branches.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "asset_tag", name="uq_clinic_asset_tag"),
    )
    for column in ("clinic_id", "branch_id", "asset_type", "status"):
        op.create_index(f"ix_clinic_assets_{column}", "clinic_assets", [column])
    op.create_table(
        "asset_maintenance_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("work_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["clinic_assets.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["clinic_branches.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("clinic_id", "branch_id", "asset_id", "status"):
        op.create_index(f"ix_asset_maintenance_records_{column}", "asset_maintenance_records", [column])
    op.create_table(
        "sterilization_cycles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
        sa.Column("asset_id", sa.String(), nullable=False),
        sa.Column("cycle_reference", sa.String(), nullable=False),
        sa.Column("load_reference", sa.String(), nullable=False),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operator_name", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("recorded_by", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["clinic_assets.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["clinic_branches.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "cycle_reference", name="uq_sterilization_cycle_reference"),
    )
    for column in ("clinic_id", "branch_id", "asset_id", "result"):
        op.create_index(f"ix_sterilization_cycles_{column}", "sterilization_cycles", [column])

    op.create_table(
        "patient_message_drafts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=True),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("consent_confirmed", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
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
    for column in ("clinic_id", "branch_id", "patient_id", "status"):
        op.create_index(f"ix_patient_message_drafts_{column}", "patient_message_drafts", [column])
    op.create_table(
        "marketing_publication_drafts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("reviewed_by", sa.String(), nullable=True),
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
    for column in ("clinic_id", "branch_id", "status"):
        op.create_index(f"ix_marketing_publication_drafts_{column}", "marketing_publication_drafts", [column])
    op.create_table(
        "clinical_note_drafts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=True),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("visit_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("clinician_input", sa.Text(), nullable=False),
        sa.Column("draft_text", sa.Text(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["clinic_branches.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["patient_visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("clinic_id", "branch_id", "patient_id", "review_status"):
        op.create_index(f"ix_clinical_note_drafts_{column}", "clinical_note_drafts", [column])


def downgrade() -> None:
    for column in ("review_status", "patient_id", "branch_id", "clinic_id"):
        op.drop_index(f"ix_clinical_note_drafts_{column}", table_name="clinical_note_drafts")
    op.drop_table("clinical_note_drafts")
    for column in ("status", "branch_id", "clinic_id"):
        op.drop_index(f"ix_marketing_publication_drafts_{column}", table_name="marketing_publication_drafts")
    op.drop_table("marketing_publication_drafts")
    for column in ("status", "patient_id", "branch_id", "clinic_id"):
        op.drop_index(f"ix_patient_message_drafts_{column}", table_name="patient_message_drafts")
    op.drop_table("patient_message_drafts")
    for column in ("result", "asset_id", "branch_id", "clinic_id"):
        op.drop_index(f"ix_sterilization_cycles_{column}", table_name="sterilization_cycles")
    op.drop_table("sterilization_cycles")
    for column in ("status", "asset_id", "branch_id", "clinic_id"):
        op.drop_index(f"ix_asset_maintenance_records_{column}", table_name="asset_maintenance_records")
    op.drop_table("asset_maintenance_records")
    for column in ("status", "asset_type", "branch_id", "clinic_id"):
        op.drop_index(f"ix_clinic_assets_{column}", table_name="clinic_assets")
    op.drop_table("clinic_assets")
    for column in ("case_id", "clinic_id"):
        op.drop_index(f"ix_dental_workflow_events_{column}", table_name="dental_workflow_events")
    op.drop_table("dental_workflow_events")
    op.drop_index(
        "ix_dental_workflow_cases_clinic_type_status",
        table_name="dental_workflow_cases",
    )
    for column in ("status", "patient_id", "branch_id", "clinic_id"):
        op.drop_index(f"ix_dental_workflow_cases_{column}", table_name="dental_workflow_cases")
    op.drop_table("dental_workflow_cases")
    with op.batch_alter_table("clinics") as batch_op:
        batch_op.drop_index("ix_clinics_organization_id")
        batch_op.drop_constraint("fk_clinics_organization_id", type_="foreignkey")
        batch_op.drop_column("organization_id")
    for column in ("organization_id", "email"):
        op.drop_index(f"ix_organization_invitations_{column}", table_name="organization_invitations")
    op.drop_table("organization_invitations")
    for column in ("clinic_id", "user_id", "organization_id"):
        op.drop_index(f"ix_organization_members_{column}", table_name="organization_members")
    op.drop_table("organization_members")
    op.drop_index("ix_clinic_organizations_owner_user_id", table_name="clinic_organizations")
    op.drop_table("clinic_organizations")
