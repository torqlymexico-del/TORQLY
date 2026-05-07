"""Add vehicle.type column and make client_id nullable.

Revision ID: 20260506_0001
Revises: 20260505_0002
Create Date: 2026-05-06 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260506_0001"
down_revision = "20260505_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("vehicles") as batch_op:
        batch_op.alter_column(
            "client_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column("type", sa.String(20), nullable=True, server_default="sedan")
        )


def downgrade() -> None:
    with op.batch_alter_table("vehicles") as batch_op:
        batch_op.drop_column("type")
        batch_op.alter_column(
            "client_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
