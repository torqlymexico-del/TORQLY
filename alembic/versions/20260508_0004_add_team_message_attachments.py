"""Add attachment columns to team_messages.

Revision ID: 20260508_0004
Revises: 20260508_0003
Create Date: 2026-05-08 14:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260508_0004"
down_revision = "20260508_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("team_messages", sa.Column("attachment_url", sa.String(500), nullable=True))
    op.add_column("team_messages", sa.Column("attachment_type", sa.String(20), nullable=True))
    op.add_column("team_messages", sa.Column("attachment_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("team_messages", "attachment_name")
    op.drop_column("team_messages", "attachment_type")
    op.drop_column("team_messages", "attachment_url")
