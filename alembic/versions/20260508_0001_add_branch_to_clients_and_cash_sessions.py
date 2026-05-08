"""Add branch field to clients, cash_sessions, and service_orders.

Revision ID: 20260508_0001
Revises: 20260507_0001
Create Date: 2026-05-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260508_0001"
down_revision = "20260507_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients",
        sa.Column("branch", sa.String(20), nullable=False, server_default="local"))
    op.add_column("cash_sessions",
        sa.Column("branch", sa.String(20), nullable=False, server_default="local"))
    op.add_column("service_orders",
        sa.Column("branch", sa.String(20), nullable=False, server_default="local"))
    # Back-fill domicilio orders
    op.execute("UPDATE service_orders SET branch = 'domicilios' WHERE is_domicilio = 1")


def downgrade() -> None:
    op.drop_column("clients", "branch")
    op.drop_column("cash_sessions", "branch")
    op.drop_column("service_orders", "branch")
