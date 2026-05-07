"""Add extended fields to cash_sessions (credit, courtesy, deposit, change_given).

Revision ID: 20260507_0001
Revises: 20260506_0001
Create Date: 2026-05-07 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260507_0001"
down_revision = "20260506_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cash_sessions", sa.Column("total_sales_credit", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("cash_sessions", sa.Column("total_sales_courtesy", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("cash_sessions", sa.Column("total_sales_deposit", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("cash_sessions", sa.Column("courtesy_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("cash_sessions", sa.Column("change_given", sa.Numeric(10, 2), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("cash_sessions", "change_given")
    op.drop_column("cash_sessions", "courtesy_count")
    op.drop_column("cash_sessions", "total_sales_deposit")
    op.drop_column("cash_sessions", "total_sales_courtesy")
    op.drop_column("cash_sessions", "total_sales_credit")
