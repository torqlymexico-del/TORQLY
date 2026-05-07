"""Phase 3 channels, notifications and external task sync.

Revision ID: 20260424_0003
Revises: 20260424_0002
Create Date: 2026-04-24 16:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_0003"
down_revision = "20260424_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("clickup_user_id", sa.String(length=64), nullable=True))
    op.create_index("ix_users_clickup_user_id", "users", ["clickup_user_id"], unique=False)

    op.add_column("appointments", sa.Column("clickup_task_url", sa.String(length=255), nullable=True))

    op.add_column(
        "whatsapp_conversations",
        sa.Column("bot_state", sa.String(length=30), nullable=False, server_default="new"),
    )
    op.create_index(
        "ix_whatsapp_conversations_bot_state",
        "whatsapp_conversations",
        ["bot_state"],
        unique=False,
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False, server_default="info"),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"], unique=False)
    op.create_index("ix_notifications_type", "notifications", ["type"], unique=False)
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_appointment_id", "notifications", ["appointment_id"], unique=False)
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_appointment_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_whatsapp_conversations_bot_state", table_name="whatsapp_conversations")
    op.drop_column("whatsapp_conversations", "bot_state")

    op.drop_column("appointments", "clickup_task_url")

    op.drop_index("ix_users_clickup_user_id", table_name="users")
    op.drop_column("users", "clickup_user_id")
