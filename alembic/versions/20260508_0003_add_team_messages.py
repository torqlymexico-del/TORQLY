"""Add team_messages table for in-app team chat.

Revision ID: 20260508_0003
Revises: 20260508_0002
Create Date: 2026-05-08 13:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260508_0003"
down_revision = "20260508_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_team_messages_id", "team_messages", ["id"])
    op.create_index("ix_team_messages_company_id", "team_messages", ["company_id"])
    op.create_index("ix_team_messages_user_id", "team_messages", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_team_messages_user_id", table_name="team_messages")
    op.drop_index("ix_team_messages_company_id", table_name="team_messages")
    op.drop_index("ix_team_messages_id", table_name="team_messages")
    op.drop_table("team_messages")
