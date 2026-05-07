"""Google OAuth login and privacy policy acceptance.

Revision ID: 20260426_0006
Revises: 20260425_0005
Create Date: 2026-04-26 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260426_0006"
down_revision = "20260425_0005"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _column_names(table_name: str) -> set[str]:
    return {col["name"] for col in _inspector().get_columns(table_name)}


def upgrade() -> None:
    cols = _column_names("users")

    # Use batch mode for SQLite compatibility (recreates the table internally)
    with op.batch_alter_table("users") as batch_op:
        # Make phone nullable
        if "phone" in cols:
            batch_op.alter_column(
                "phone",
                existing_type=sa.String(25),
                nullable=True,
            )
        # Make password_hash nullable
        if "password_hash" in cols:
            batch_op.alter_column(
                "password_hash",
                existing_type=sa.String(255),
                nullable=True,
            )
        # Add new columns
        if "google_sub" not in cols:
            batch_op.add_column(sa.Column("google_sub", sa.String(128), nullable=True))
        if "privacy_policy_accepted_at" not in cols:
            batch_op.add_column(
                sa.Column("privacy_policy_accepted_at", sa.DateTime(timezone=True), nullable=True)
            )
        if "privacy_policy_version" not in cols:
            batch_op.add_column(
                sa.Column("privacy_policy_version", sa.String(20), nullable=True)
            )

    # Create unique index for google_sub outside batch (batch recreates table, index goes after)
    if "google_sub" not in cols:
        op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)


def downgrade() -> None:
    cols = _column_names("users")

    if "google_sub" in cols:
        op.drop_index("ix_users_google_sub", table_name="users")

    with op.batch_alter_table("users") as batch_op:
        if "privacy_policy_version" in cols:
            batch_op.drop_column("privacy_policy_version")
        if "privacy_policy_accepted_at" in cols:
            batch_op.drop_column("privacy_policy_accepted_at")
        if "google_sub" in cols:
            batch_op.drop_column("google_sub")
        # Restore NOT NULL
        if "password_hash" in cols:
            batch_op.alter_column(
                "password_hash",
                existing_type=sa.String(255),
                nullable=False,
            )
        if "phone" in cols:
            batch_op.alter_column(
                "phone",
                existing_type=sa.String(25),
                nullable=False,
            )
