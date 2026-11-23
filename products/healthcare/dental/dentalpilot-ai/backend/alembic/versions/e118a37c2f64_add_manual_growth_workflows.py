"""Add manual clinic growth, campaign, and review workflows.

Revision ID: e118a37c2f64
Revises: d2e83f451a70
Create Date: 2026-11-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e118a37c2f64"
down_revision: Union[str, Sequence[str], None] = "d2e83f451a70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "local_listing_audits",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("profile_url", sa.String(), nullable=False),
        sa.Column("primary_category", sa.String(), nullable=False),
        sa.Column("name_matches", sa.Boolean(), nullable=False),
        sa.Column("address_matches", sa.Boolean(), nullable=False),
        sa.Column("phone_matches", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column(
            "last_reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["clinic_branches.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("branch_id", "platform", name="uq_local_listing_branch_platform"),
    )
    op.create_index("ix_local_listing_audits_clinic_id", "local_listing_audits", ["clinic_id"])
    op.create_index("ix_local_listing_audits_branch_id", "local_listing_audits", ["branch_id"])

    op.create_table(
        "marketing_campaigns",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
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
    )
    op.create_index("ix_marketing_campaigns_clinic_id", "marketing_campaigns", ["clinic_id"])
    op.create_index("ix_marketing_campaigns_branch_id", "marketing_campaigns", ["branch_id"])

    op.create_table(
        "clinic_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=True),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("reviewer_name", sa.String(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column("response_draft", sa.Text(), nullable=True),
        sa.Column("response_status", sa.String(), nullable=False),
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_index("ix_clinic_reviews_clinic_id", "clinic_reviews", ["clinic_id"])
    op.create_index("ix_clinic_reviews_branch_id", "clinic_reviews", ["branch_id"])


def downgrade() -> None:
    op.drop_index("ix_clinic_reviews_branch_id", table_name="clinic_reviews")
    op.drop_index("ix_clinic_reviews_clinic_id", table_name="clinic_reviews")
    op.drop_table("clinic_reviews")
    op.drop_index("ix_marketing_campaigns_branch_id", table_name="marketing_campaigns")
    op.drop_index("ix_marketing_campaigns_clinic_id", table_name="marketing_campaigns")
    op.drop_table("marketing_campaigns")
    op.drop_index("ix_local_listing_audits_branch_id", table_name="local_listing_audits")
    op.drop_index("ix_local_listing_audits_clinic_id", table_name="local_listing_audits")
    op.drop_table("local_listing_audits")
