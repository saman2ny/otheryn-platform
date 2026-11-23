"""Add treatment checkout, insurance claims, and PMS CSV reconciliation.

Revision ID: 9e3f6a4b2c10
Revises: b7f4e62a19c3
Create Date: 2026-11-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9e3f6a4b2c10"
down_revision: Union[str, Sequence[str], None] = "b7f4e62a19c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("treatment_ledger_entries") as batch_op:
        batch_op.add_column(sa.Column("charge_entry_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_treatment_ledger_charge_entry",
            "treatment_ledger_entries",
            ["charge_entry_id"],
            ["id"],
        )
        batch_op.create_index("ix_treatment_ledger_entries_charge_entry_id", ["charge_entry_id"])

    op.create_table(
        "patient_payment_orders",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=True),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("charge_entry_id", sa.String(), nullable=False),
        sa.Column("payment_ledger_entry_id", sa.String(), nullable=True),
        sa.Column("razorpay_order_id", sa.String(), nullable=False),
        sa.Column("razorpay_payment_id", sa.String(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_subunits", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "initiated_by_patient",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["clinic_branches.id"]),
        sa.ForeignKeyConstraint(["charge_entry_id"], ["treatment_ledger_entries.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["payment_ledger_entry_id"], ["treatment_ledger_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_ledger_entry_id"),
        sa.UniqueConstraint("razorpay_payment_id"),
    )
    for column in ("clinic_id", "branch_id", "patient_id", "charge_entry_id", "status", "created_at"):
        op.create_index(f"ix_patient_payment_orders_{column}", "patient_payment_orders", [column])
    op.create_index(
        "ix_patient_payment_orders_razorpay_order_id",
        "patient_payment_orders",
        ["razorpay_order_id"],
        unique=True,
    )
    op.create_index(
        "uq_patient_payment_order_open_charge",
        "patient_payment_orders",
        ["charge_entry_id"],
        unique=True,
        sqlite_where=sa.text("status = 'created'"),
        postgresql_where=sa.text("status = 'created'"),
    )

    op.create_table(
        "insurance_claims",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=True),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("charge_entry_id", sa.String(), nullable=True),
        sa.Column("supporting_record_id", sa.String(), nullable=True),
        sa.Column("payer_name", sa.String(), nullable=False),
        sa.Column("claim_number", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("billed_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("approved_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("denial_reason", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
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
        sa.ForeignKeyConstraint(["charge_entry_id"], ["treatment_ledger_entries.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["supporting_record_id"], ["health_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("clinic_id", "branch_id", "patient_id", "charge_entry_id", "status", "created_at"):
        op.create_index(f"ix_insurance_claims_{column}", "insurance_claims", [column])
    op.create_index(
        "uq_insurance_claim_clinic_payer_number",
        "insurance_claims",
        ["clinic_id", "payer_name", "claim_number"],
        unique=True,
        sqlite_where=sa.text("claim_number <> ''"),
        postgresql_where=sa.text("claim_number <> ''"),
    )

    op.create_table(
        "pms_reconciliation_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("matched_rows", sa.Integer(), nullable=False),
        sa.Column("mismatch_rows", sa.Integer(), nullable=False),
        sa.Column("missing_local_rows", sa.Integer(), nullable=False),
        sa.Column("missing_pms_rows", sa.Integer(), nullable=False),
        sa.Column("duplicate_source_rows", sa.Integer(), nullable=False),
        sa.Column("invalid_rows", sa.Integer(), nullable=False),
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
    for column in ("clinic_id", "branch_id", "created_at"):
        op.create_index(f"ix_pms_reconciliation_runs_{column}", "pms_reconciliation_runs", [column])

    op.create_table(
        "pms_reconciliation_rows",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("transaction_reference", sa.String(), nullable=False),
        sa.Column("patient_reference", sa.String(), nullable=False),
        sa.Column("local_ledger_entry_id", sa.String(), nullable=True),
        sa.Column("entry_type", sa.String(), nullable=True),
        sa.Column("external_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("local_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["local_ledger_entry_id"], ["treatment_ledger_entries.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["pms_reconciliation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("run_id", "clinic_id", "status"):
        op.create_index(f"ix_pms_reconciliation_rows_{column}", "pms_reconciliation_rows", [column])


def downgrade() -> None:
    op.drop_index("ix_pms_reconciliation_rows_status", table_name="pms_reconciliation_rows")
    op.drop_index("ix_pms_reconciliation_rows_clinic_id", table_name="pms_reconciliation_rows")
    op.drop_index("ix_pms_reconciliation_rows_run_id", table_name="pms_reconciliation_rows")
    op.drop_table("pms_reconciliation_rows")
    op.drop_index("ix_pms_reconciliation_runs_created_at", table_name="pms_reconciliation_runs")
    op.drop_index("ix_pms_reconciliation_runs_branch_id", table_name="pms_reconciliation_runs")
    op.drop_index("ix_pms_reconciliation_runs_clinic_id", table_name="pms_reconciliation_runs")
    op.drop_table("pms_reconciliation_runs")
    op.drop_index("uq_insurance_claim_clinic_payer_number", table_name="insurance_claims")
    for column in ("created_at", "status", "charge_entry_id", "patient_id", "branch_id", "clinic_id"):
        op.drop_index(f"ix_insurance_claims_{column}", table_name="insurance_claims")
    op.drop_table("insurance_claims")
    op.drop_index("uq_patient_payment_order_open_charge", table_name="patient_payment_orders")
    for column in ("created_at", "status", "razorpay_order_id", "charge_entry_id", "patient_id", "branch_id", "clinic_id"):
        op.drop_index(f"ix_patient_payment_orders_{column}", table_name="patient_payment_orders")
    op.drop_table("patient_payment_orders")
    with op.batch_alter_table("treatment_ledger_entries") as batch_op:
        batch_op.drop_index("ix_treatment_ledger_entries_charge_entry_id")
        batch_op.drop_constraint("fk_treatment_ledger_charge_entry", type_="foreignkey")
        batch_op.drop_column("charge_entry_id")
