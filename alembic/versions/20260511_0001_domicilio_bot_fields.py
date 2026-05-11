"""Add domicilio bot fields: client defaults, appointment GPS coordinates.

Revision ID: 20260511_0001
Revises: 20260508_0008
Create Date: 2026-05-11 12:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260511_0001"
down_revision = "20260508_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # GPS coordinates on appointments (for domicilio)
    op.add_column("appointments", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("appointments", sa.Column("longitude", sa.Float(), nullable=True))

    # Default vehicle and service on clients (for quick re-booking via WhatsApp)
    op.add_column(
        "clients",
        sa.Column(
            "default_vehicle_id",
            sa.Integer(),
            sa.ForeignKey("vehicles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "clients",
        sa.Column(
            "default_service_id",
            sa.Integer(),
            sa.ForeignKey("services_catalog.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("clients", "default_service_id")
    op.drop_column("clients", "default_vehicle_id")
    op.drop_column("appointments", "longitude")
    op.drop_column("appointments", "latitude")
