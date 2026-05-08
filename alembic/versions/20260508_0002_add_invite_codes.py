"""Add invite_codes table for role-based registration.

Revision ID: 20260508_0002
Revises: 20260508_0001
Create Date: 2026-05-08 12:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260508_0002"
down_revision = "20260508_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invite_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("label", sa.String(80), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("used_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_invite_codes_id", "invite_codes", ["id"])
    op.create_index("ix_invite_codes_code", "invite_codes", ["code"], unique=True)
    op.create_index("ix_invite_codes_company_id", "invite_codes", ["company_id"])
    op.create_index("ix_invite_codes_created_by_id", "invite_codes", ["created_by_id"])


def downgrade() -> None:
    op.drop_index("ix_invite_codes_created_by_id", table_name="invite_codes")
    op.drop_index("ix_invite_codes_company_id", table_name="invite_codes")
    op.drop_index("ix_invite_codes_code", table_name="invite_codes")
    op.drop_index("ix_invite_codes_id", table_name="invite_codes")
    op.drop_table("invite_codes")
