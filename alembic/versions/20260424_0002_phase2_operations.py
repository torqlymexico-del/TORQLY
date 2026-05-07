"""Phase 2 operations schema updates.

Revision ID: 20260424_0002
Revises: 20260424_0001
Create Date: 2026-04-24 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_0002"
down_revision = "20260424_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    op.add_column(
        "appointments",
        sa.Column("charge_status", sa.String(length=30), nullable=False, server_default="pendiente"),
    )
    op.add_column("appointments", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("payments", sa.Column("ticket_number", sa.String(length=40), nullable=True))
    op.add_column("payments", sa.Column("reference", sa.String(length=120), nullable=True))
    op.create_index("ix_payments_ticket_number", "payments", ["ticket_number"], unique=True)

    op.add_column(
        "payment_items",
        sa.Column("item_type", sa.String(length=30), nullable=False, server_default="service"),
    )
    op.add_column(
        "payment_items",
        sa.Column("apply_commission", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )

    op.add_column("cash_cuts", sa.Column("opened_by_user_id", sa.Integer(), nullable=True))
    op.add_column("cash_cuts", sa.Column("closed_by_user_id", sa.Integer(), nullable=True))
    op.add_column("cash_cuts", sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cash_cuts", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "cash_cuts",
        sa.Column("cost_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "cash_cuts",
        sa.Column("services_charged", sa.Integer(), nullable=False, server_default="0"),
    )
    if dialect_name != "sqlite":
        op.create_foreign_key(
            "fk_cash_cuts_opened_by_user_id_users",
            "cash_cuts",
            "users",
            ["opened_by_user_id"],
            ["id"],
        )
        op.create_foreign_key(
            "fk_cash_cuts_closed_by_user_id_users",
            "cash_cuts",
            "users",
            ["closed_by_user_id"],
            ["id"],
        )
    op.create_index("ix_cash_cuts_opened_by_user_id", "cash_cuts", ["opened_by_user_id"], unique=False)
    op.create_index("ix_cash_cuts_closed_by_user_id", "cash_cuts", ["closed_by_user_id"], unique=False)


def downgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    op.drop_index("ix_cash_cuts_closed_by_user_id", table_name="cash_cuts")
    op.drop_index("ix_cash_cuts_opened_by_user_id", table_name="cash_cuts")
    if dialect_name != "sqlite":
        op.drop_constraint("fk_cash_cuts_closed_by_user_id_users", "cash_cuts", type_="foreignkey")
        op.drop_constraint("fk_cash_cuts_opened_by_user_id_users", "cash_cuts", type_="foreignkey")
    op.drop_column("cash_cuts", "services_charged")
    op.drop_column("cash_cuts", "cost_total")
    op.drop_column("cash_cuts", "closed_at")
    op.drop_column("cash_cuts", "opened_at")
    op.drop_column("cash_cuts", "closed_by_user_id")
    op.drop_column("cash_cuts", "opened_by_user_id")

    op.drop_column("payment_items", "apply_commission")
    op.drop_column("payment_items", "item_type")

    op.drop_index("ix_payments_ticket_number", table_name="payments")
    op.drop_column("payments", "reference")
    op.drop_column("payments", "ticket_number")

    op.drop_column("appointments", "paid_at")
    op.drop_column("appointments", "charge_status")
