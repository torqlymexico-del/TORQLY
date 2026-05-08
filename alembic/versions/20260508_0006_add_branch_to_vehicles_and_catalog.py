"""Add branch isolation to vehicles, services_catalog, catalog_families.

Revision ID: 20260508_0006
Revises: 20260508_0005
Create Date: 2026-05-08 16:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260508_0006"
down_revision = "20260508_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # vehicles
    op.add_column("vehicles", sa.Column("branch", sa.String(20), nullable=False, server_default="local"))
    op.create_index("ix_vehicles_branch", "vehicles", ["branch"])

    # services_catalog: drop global unique on name, add branch column
    op.drop_index("ix_services_catalog_name", table_name="services_catalog")
    op.add_column("services_catalog", sa.Column("branch", sa.String(20), nullable=False, server_default="local"))
    op.create_index("ix_services_catalog_name", "services_catalog", ["name"], unique=False)
    op.create_index("ix_services_catalog_branch", "services_catalog", ["branch"])

    # catalog_families
    op.add_column("catalog_families", sa.Column("branch", sa.String(20), nullable=False, server_default="local"))
    op.create_index("ix_catalog_families_branch", "catalog_families", ["branch"])


def downgrade() -> None:
    op.drop_index("ix_catalog_families_branch", table_name="catalog_families")
    op.drop_column("catalog_families", "branch")

    op.drop_index("ix_services_catalog_branch", table_name="services_catalog")
    op.drop_index("ix_services_catalog_name", table_name="services_catalog")
    op.drop_column("services_catalog", "branch")
    op.create_index("ix_services_catalog_name", "services_catalog", ["name"], unique=True)

    op.drop_index("ix_vehicles_branch", table_name="vehicles")
    op.drop_column("vehicles", "branch")
