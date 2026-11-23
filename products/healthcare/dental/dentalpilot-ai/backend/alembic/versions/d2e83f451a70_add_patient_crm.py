"""Add enquiry tracking and patient communication history.

Revision ID: d2e83f451a70
Revises: f1a9c5e0d4b7
Create Date: 2026-11-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2e83f451a70"
down_revision: Union[str, Sequence[str], None] = "f1a9c5e0d4b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patient_enquiries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("requested_service", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_enquiries_clinic_id", "patient_enquiries", ["clinic_id"])
    op.create_index("ix_patient_enquiries_branch_id", "patient_enquiries", ["branch_id"])
    op.create_index("ix_patient_enquiries_patient_id", "patient_enquiries", ["patient_id"])

    op.create_table(
        "patient_communications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_communications_clinic_id", "patient_communications", ["clinic_id"])
    op.create_index("ix_patient_communications_patient_id", "patient_communications", ["patient_id"])
    op.create_index("ix_patient_communications_created_at", "patient_communications", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_patient_communications_created_at", table_name="patient_communications")
    op.drop_index("ix_patient_communications_patient_id", table_name="patient_communications")
    op.drop_index("ix_patient_communications_clinic_id", table_name="patient_communications")
    op.drop_table("patient_communications")
    op.drop_index("ix_patient_enquiries_patient_id", table_name="patient_enquiries")
    op.drop_index("ix_patient_enquiries_branch_id", table_name="patient_enquiries")
    op.drop_index("ix_patient_enquiries_clinic_id", table_name="patient_enquiries")
    op.drop_table("patient_enquiries")
