"""Phase 4 bot, scheduler and stock automation fields.

Revision ID: 20260425_0004
Revises: 20260424_0003
Create Date: 2026-04-25 09:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260425_0004"
down_revision = "20260424_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "appointments",
        sa.Column("operator_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column("ready_for_charge_notified_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "inventory_products",
        sa.Column("low_stock_notified_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "internal_bot_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=60), nullable=False, server_default="unknown"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="unknown"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_internal_bot_messages_id", "internal_bot_messages", ["id"], unique=False)
    op.create_index("ix_internal_bot_messages_user_id", "internal_bot_messages", ["user_id"], unique=False)
    op.create_index("ix_internal_bot_messages_intent", "internal_bot_messages", ["intent"], unique=False)
    op.create_index("ix_internal_bot_messages_status", "internal_bot_messages", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_internal_bot_messages_status", table_name="internal_bot_messages")
    op.drop_index("ix_internal_bot_messages_intent", table_name="internal_bot_messages")
    op.drop_index("ix_internal_bot_messages_user_id", table_name="internal_bot_messages")
    op.drop_index("ix_internal_bot_messages_id", table_name="internal_bot_messages")
    op.drop_table("internal_bot_messages")

    op.drop_column("inventory_products", "low_stock_notified_at")

    op.drop_column("appointments", "ready_for_charge_notified_at")
    op.drop_column("appointments", "operator_reminder_sent_at")
    op.drop_column("appointments", "reminder_sent_at")
