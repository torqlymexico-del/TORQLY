"""Add accounting tables: settings, fixed_costs, fixed_assets, payables, equity_movements, movement_categories.

Revision ID: 20260519_0001
Revises: 20260511_0001
Create Date: 2026-05-19 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260519_0001"
down_revision = "20260511_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounting_settings",
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), primary_key=True),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default="16.00"),
        sa.Column("monthly_depreciation", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("monthly_external_fees", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("target_net_margin", sa.Numeric(5, 2), nullable=False, server_default="15.00"),
        sa.Column("closing_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("opening_retained_earnings", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("opening_retained_earnings_notes", sa.Text(), nullable=True),
        sa.Column("opening_cash_balance", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("opening_cash_balance_date", sa.Date(), nullable=True),
        sa.Column("opening_domicilios_balance", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("opening_domicilios_balance_date", sa.Date(), nullable=True),
        sa.Column("payroll_liability_basis", sa.String(30), nullable=False, server_default="weekly_current"),
        sa.Column("payroll_liability_manual", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("cleanup_notes", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "accounting_fixed_costs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(80), nullable=False, server_default="General"),
        sa.Column("monthly_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "accounting_fixed_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("asset_name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(80), nullable=False, server_default="Activo fijo"),
        sa.Column("acquisition_date", sa.Date(), nullable=False),
        sa.Column("acquisition_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("salvage_value", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("useful_life_months", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "accounting_payables",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("vendor_name", sa.String(120), nullable=False),
        sa.Column("concept", sa.String(160), nullable=False),
        sa.Column("category", sa.String(80), nullable=False, server_default="General"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("payment_method", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "accounting_equity_movements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("movement_type", sa.String(20), nullable=False, server_default="contribution"),
        sa.Column("concept", sa.String(160), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("movement_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "accounting_movement_categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("raw_category", sa.String(80), nullable=False),
        sa.Column("classification", sa.String(40), nullable=False, server_default="unclassified"),
        sa.Column("display_label", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("company_id", "source_type", "raw_category", name="uq_acc_movement_cat"),
    )


def downgrade() -> None:
    op.drop_table("accounting_movement_categories")
    op.drop_table("accounting_equity_movements")
    op.drop_table("accounting_payables")
    op.drop_table("accounting_fixed_assets")
    op.drop_table("accounting_fixed_costs")
    op.drop_table("accounting_settings")
