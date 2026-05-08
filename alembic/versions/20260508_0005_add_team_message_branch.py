"""Add branch column to team_messages.

Revision ID: 20260508_0005
Revises: 20260508_0004
Create Date: 2026-05-08 15:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260508_0005"
down_revision = "20260508_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "team_messages",
        sa.Column("branch", sa.String(30), nullable=False, server_default="local"),
    )
    op.create_index("ix_team_messages_branch", "team_messages", ["branch"])


def downgrade() -> None:
    op.drop_index("ix_team_messages_branch", table_name="team_messages")
    op.drop_column("team_messages", "branch")
