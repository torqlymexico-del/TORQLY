"""Add branch to users and invite_codes.

Revision ID: 20260508_0007
Revises: 20260508_0006
Create Date: 2026-05-08 17:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260508_0007"
down_revision = "20260508_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("branch", sa.String(20), nullable=False, server_default="local"))
    op.create_index("ix_users_branch", "users", ["branch"])

    op.add_column("invite_codes", sa.Column("branch", sa.String(20), nullable=False, server_default="local"))


def downgrade() -> None:
    op.drop_column("invite_codes", "branch")
    op.drop_index("ix_users_branch", table_name="users")
    op.drop_column("users", "branch")
