"""patient intelligence

Revision ID: 20261124000000
Revises: e78cbd0fad9c
Create Date: 2026-11-24

Adds structured patient medical history, dental history, emergency contacts,
update metadata and a revision log for patient record updates.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261124000000"
down_revision = "e78cbd0fad9c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("medical_history", sa.JSON(), nullable=True))
    op.add_column("patients", sa.Column("dental_history", sa.JSON(), nullable=True))
    op.add_column("patients", sa.Column("emergency_contacts", sa.JSON(), nullable=True))
    op.add_column("patients", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("patients", sa.Column("updated_by", sa.String(), nullable=True))

    op.create_table(
        "patient_revisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("clinic_id", sa.String(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", sa.String(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_patient_revisions_clinic_id", "patient_revisions", ["clinic_id"]
    )
    op.create_index(
        "ix_patient_revisions_patient_id", "patient_revisions", ["patient_id"]
    )
    op.create_unique_constraint(
        "uq_patient_revision_version", "patient_revisions", ["patient_id", "version"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_patient_revision_version", "patient_revisions", type_="unique"
    )
    op.drop_index("ix_patient_revisions_patient_id", table_name="patient_revisions")
    op.drop_index("ix_patient_revisions_clinic_id", table_name="patient_revisions")
    op.drop_table("patient_revisions")
    op.drop_column("patients", "updated_by")
    op.drop_column("patients", "updated_at")
    op.drop_column("patients", "emergency_contacts")
    op.drop_column("patients", "dental_history")
    op.drop_column("patients", "medical_history")