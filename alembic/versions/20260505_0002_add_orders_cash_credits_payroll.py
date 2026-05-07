"""Add orders, cash sessions, credits, payroll, catalog families.

Revision ID: 20260505_0002
Revises: 20260426_0006
Create Date: 2026-05-05 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260505_0002"
down_revision = "20260426_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Catalog families & subfamilies ───────────────────────────────────────
    op.create_table(
        "catalog_families",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color_code", sa.String(7), nullable=False, server_default="#334155"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_catalog_families_id", "catalog_families", ["id"])

    op.create_table(
        "catalog_subfamilies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("family_id", sa.Integer(), sa.ForeignKey("catalog_families.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_catalog_subfamilies_id", "catalog_subfamilies", ["id"])
    op.create_index("ix_catalog_subfamilies_family_id", "catalog_subfamilies", ["family_id"])

    # ── New columns on services_catalog ─────────────────────────────────────
    op.add_column("services_catalog", sa.Column("subfamily_id", sa.Integer(), nullable=True))
    op.add_column("services_catalog", sa.Column("suggested_commission_percent", sa.Numeric(5, 2), nullable=False, server_default="30"))
    op.add_column("services_catalog", sa.Column("color_code", sa.String(7), nullable=False, server_default="#334155"))
    op.add_column("services_catalog", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_services_catalog_subfamily_id", "services_catalog", ["subfamily_id"])

    # ── Cash sessions ────────────────────────────────────────────────────────
    op.create_table(
        "cash_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("opened_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("opening_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("closed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closing_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("expected_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("difference_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("total_sales_cash", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total_sales_card", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total_sales_transfer", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total_sales", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total_expenses", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="abierta"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_cash_sessions_id", "cash_sessions", ["id"])
    op.create_index("ix_cash_sessions_company_id", "cash_sessions", ["company_id"])
    op.create_index("ix_cash_sessions_status", "cash_sessions", ["status"])

    # ── Service orders ───────────────────────────────────────────────────────
    op.create_table(
        "service_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("cash_session_id", sa.Integer(), sa.ForeignKey("cash_sessions.id"), nullable=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=True),
        sa.Column("daily_sequence", sa.Integer(), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("discount_reason", sa.String(100), nullable=True),
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="en_cola"),
        sa.Column("payment_status", sa.String(30), nullable=False, server_default="pendiente"),
        sa.Column("payment_method", sa.String(30), nullable=True),
        sa.Column("is_domicilio", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("delivery_address", sa.String(255), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cancelled_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_service_orders_id", "service_orders", ["id"])
    op.create_index("ix_service_orders_company_id", "service_orders", ["company_id"])
    op.create_index("ix_service_orders_cash_session_id", "service_orders", ["cash_session_id"])
    op.create_index("ix_service_orders_client_id", "service_orders", ["client_id"])
    op.create_index("ix_service_orders_vehicle_id", "service_orders", ["vehicle_id"])
    op.create_index("ix_service_orders_service_date", "service_orders", ["service_date"])
    op.create_index("ix_service_orders_status", "service_orders", ["status"])

    # ── Service order items ──────────────────────────────────────────────────
    op.create_table(
        "service_order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_id", sa.Integer(), sa.ForeignKey("services_catalog.id"), nullable=True),
        sa.Column("custom_name", sa.String(120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_service_order_items_id", "service_order_items", ["id"])
    op.create_index("ix_service_order_items_order_id", "service_order_items", ["order_id"])

    # ── Service order washers ────────────────────────────────────────────────
    op.create_table(
        "service_order_washers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("commission_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("commission_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_service_order_washers_id", "service_order_washers", ["id"])
    op.create_index("ix_service_order_washers_order_id", "service_order_washers", ["order_id"])
    op.create_index("ix_service_order_washers_user_id", "service_order_washers", ["user_id"])

    # ── Cash movements ───────────────────────────────────────────────────────
    op.create_table(
        "cash_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("cash_sessions.id"), nullable=False),
        sa.Column("movement_type", sa.String(20), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="general"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_void", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("service_orders.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_cash_movements_id", "cash_movements", ["id"])
    op.create_index("ix_cash_movements_session_id", "cash_movements", ["session_id"])

    # ── Client credit accounts ───────────────────────────────────────────────
    op.create_table(
        "client_credit_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("credit_limit", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("current_balance", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_client_credit_accounts_id", "client_credit_accounts", ["id"])
    op.create_index("ix_client_credit_accounts_client_id", "client_credit_accounts", ["client_id"], unique=True)

    op.create_table(
        "client_credit_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("client_credit_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("service_orders.id"), nullable=True),
        sa.Column("movement_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_client_credit_movements_id", "client_credit_movements", ["id"])
    op.create_index("ix_client_credit_movements_account_id", "client_credit_movements", ["account_id"])
    op.create_index("ix_client_credit_movements_client_id", "client_credit_movements", ["client_id"])

    # ── Payroll ──────────────────────────────────────────────────────────────
    op.create_table(
        "payroll_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True, unique=True),
        sa.Column("rag_unit_price", sa.Numeric(10, 2), nullable=False, server_default="20"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_payroll_settings_id", "payroll_settings", ["id"])

    op.create_table(
        "payroll_deductions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deduction_type", sa.String(30), nullable=False, server_default="trapos"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_payroll_deductions_id", "payroll_deductions", ["id"])
    op.create_index("ix_payroll_deductions_user_id", "payroll_deductions", ["user_id"])

    op.create_table(
        "commission_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_source", sa.String(20), nullable=False, server_default="efectivo"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("paid_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cash_session_id", sa.Integer(), sa.ForeignKey("cash_sessions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_commission_payments_id", "commission_payments", ["id"])
    op.create_index("ix_commission_payments_user_id", "commission_payments", ["user_id"])

    op.create_table(
        "salary_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_source", sa.String(20), nullable=False, server_default="efectivo"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("paid_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cash_session_id", sa.Integer(), sa.ForeignKey("cash_sessions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_salary_payments_id", "salary_payments", ["id"])
    op.create_index("ix_salary_payments_user_id", "salary_payments", ["user_id"])


def downgrade() -> None:
    op.drop_table("salary_payments")
    op.drop_table("commission_payments")
    op.drop_table("payroll_deductions")
    op.drop_table("payroll_settings")
    op.drop_table("client_credit_movements")
    op.drop_table("client_credit_accounts")
    op.drop_table("cash_movements")
    op.drop_table("service_order_washers")
    op.drop_table("service_order_items")
    op.drop_table("service_orders")
    op.drop_table("cash_sessions")
    op.drop_column("services_catalog", "sort_order")
    op.drop_column("services_catalog", "color_code")
    op.drop_column("services_catalog", "suggested_commission_percent")
    op.drop_column("services_catalog", "subfamily_id")
    op.drop_table("catalog_subfamilies")
    op.drop_table("catalog_families")
