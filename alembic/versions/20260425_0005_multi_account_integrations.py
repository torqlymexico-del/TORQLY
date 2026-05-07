"""Multi-account integration management.

Revision ID: 20260425_0005
Revises: 20260425_0004
Create Date: 2026-04-25 11:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260425_0005"
down_revision = "20260425_0004"
branch_labels = None
depends_on = None


def _slugify(value: str) -> str:
    return "-".join((value or "").lower().strip().split()) or "empresa-principal"


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _column_names(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def _foreign_key_names(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {fk["name"] for fk in _inspector().get_foreign_keys(table_name) if fk.get("name")}


def _batch_mode() -> str:
    return "always" if op.get_bind().dialect.name == "sqlite" else "auto"


def _ensure_companies() -> None:
    if not _has_table("companies"):
        op.create_table(
            "companies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False, unique=True),
            sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    indexes = _index_names("companies")
    if "ix_companies_id" not in indexes:
        op.create_index("ix_companies_id", "companies", ["id"], unique=False)
    if "ix_companies_slug" not in indexes:
        op.create_index("ix_companies_slug", "companies", ["slug"], unique=True)


def _ensure_users_columns() -> None:
    columns = _column_names("users")
    indexes = _index_names("users")
    foreign_keys = _foreign_key_names("users")

    with op.batch_alter_table("users", recreate=_batch_mode()) as batch_op:
        if "company_id" not in columns:
            batch_op.add_column(sa.Column("company_id", sa.Integer(), nullable=True))
        if "active_company_id" not in columns:
            batch_op.add_column(sa.Column("active_company_id", sa.Integer(), nullable=True))
        if "permissions" not in columns:
            batch_op.add_column(sa.Column("permissions", sa.JSON(), nullable=True))

        if "ix_users_company_id" not in indexes:
            batch_op.create_index("ix_users_company_id", ["company_id"], unique=False)
        if "ix_users_active_company_id" not in indexes:
            batch_op.create_index("ix_users_active_company_id", ["active_company_id"], unique=False)

        if "fk_users_company_id" not in foreign_keys:
            batch_op.create_foreign_key("fk_users_company_id", "companies", ["company_id"], ["id"])
        if "fk_users_active_company_id" not in foreign_keys:
            batch_op.create_foreign_key(
                "fk_users_active_company_id",
                "companies",
                ["active_company_id"],
                ["id"],
            )


def _ensure_integration_accounts() -> None:
    if not _has_table("integration_accounts"):
        op.create_table(
            "integration_accounts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="inactive"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("credentials_encrypted", sa.Text(), nullable=True),
            sa.Column("config_json", sa.JSON(), nullable=True),
            sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    indexes = _index_names("integration_accounts")
    if "ix_integration_accounts_id" not in indexes:
        op.create_index("ix_integration_accounts_id", "integration_accounts", ["id"], unique=False)
    if "ix_integration_accounts_company_id" not in indexes:
        op.create_index(
            "ix_integration_accounts_company_id",
            "integration_accounts",
            ["company_id"],
            unique=False,
        )
    if "ix_integration_accounts_provider" not in indexes:
        op.create_index(
            "ix_integration_accounts_provider",
            "integration_accounts",
            ["provider"],
            unique=False,
        )
    if "ix_integration_accounts_status" not in indexes:
        op.create_index("ix_integration_accounts_status", "integration_accounts", ["status"], unique=False)


def _ensure_external_sync_records() -> None:
    if not _has_table("external_sync_records"):
        op.create_table(
            "external_sync_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("entity_type", sa.String(length=80), nullable=False),
            sa.Column("entity_id", sa.String(length=120), nullable=False),
            sa.Column("external_id", sa.String(length=255), nullable=False),
            sa.Column("integration_account_id", sa.Integer(), sa.ForeignKey("integration_accounts.id"), nullable=True),
            sa.Column("sync_status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    indexes = _index_names("external_sync_records")
    needed_indexes = {
        "ix_external_sync_records_id": ["id"],
        "ix_external_sync_records_provider": ["provider"],
        "ix_external_sync_records_entity_type": ["entity_type"],
        "ix_external_sync_records_entity_id": ["entity_id"],
        "ix_external_sync_records_external_id": ["external_id"],
        "ix_external_sync_records_integration_account_id": ["integration_account_id"],
    }
    for index_name, columns in needed_indexes.items():
        if index_name not in indexes:
            op.create_index(index_name, "external_sync_records", columns, unique=False)


def _ensure_appointments_columns() -> None:
    columns = _column_names("appointments")
    indexes = _index_names("appointments")
    foreign_keys = _foreign_key_names("appointments")

    with op.batch_alter_table("appointments", recreate=_batch_mode()) as batch_op:
        mapping = {
            "whatsapp_integration_id": "fk_appointments_whatsapp_integration_id",
            "google_calendar_integration_id": "fk_appointments_google_calendar_integration_id",
            "google_sheets_integration_id": "fk_appointments_google_sheets_integration_id",
            "clickup_integration_id": "fk_appointments_clickup_integration_id",
            "meta_business_integration_id": "fk_appointments_meta_business_integration_id",
        }
        for column_name in mapping:
            if column_name not in columns:
                batch_op.add_column(sa.Column(column_name, sa.Integer(), nullable=True))

        index_mapping = {
            "ix_appointments_whatsapp_integration_id": ["whatsapp_integration_id"],
            "ix_appointments_google_calendar_integration_id": ["google_calendar_integration_id"],
            "ix_appointments_google_sheets_integration_id": ["google_sheets_integration_id"],
            "ix_appointments_clickup_integration_id": ["clickup_integration_id"],
            "ix_appointments_meta_business_integration_id": ["meta_business_integration_id"],
        }
        for index_name, index_columns in index_mapping.items():
            if index_name not in indexes:
                batch_op.create_index(index_name, index_columns, unique=False)

        for column_name, fk_name in mapping.items():
            if fk_name not in foreign_keys:
                batch_op.create_foreign_key(fk_name, "integration_accounts", [column_name], ["id"])


def _ensure_whatsapp_columns() -> None:
    conversation_columns = _column_names("whatsapp_conversations")
    conversation_indexes = _index_names("whatsapp_conversations")
    conversation_foreign_keys = _foreign_key_names("whatsapp_conversations")
    with op.batch_alter_table("whatsapp_conversations", recreate=_batch_mode()) as batch_op:
        if "integration_account_id" not in conversation_columns:
            batch_op.add_column(sa.Column("integration_account_id", sa.Integer(), nullable=True))
        if "ix_whatsapp_conversations_integration_account_id" not in conversation_indexes:
            batch_op.create_index(
                "ix_whatsapp_conversations_integration_account_id",
                ["integration_account_id"],
                unique=False,
            )
        if "fk_whatsapp_conversations_integration_account_id" not in conversation_foreign_keys:
            batch_op.create_foreign_key(
                "fk_whatsapp_conversations_integration_account_id",
                "integration_accounts",
                ["integration_account_id"],
                ["id"],
            )

    message_columns = _column_names("whatsapp_messages")
    message_indexes = _index_names("whatsapp_messages")
    message_foreign_keys = _foreign_key_names("whatsapp_messages")
    with op.batch_alter_table("whatsapp_messages", recreate=_batch_mode()) as batch_op:
        if "integration_account_id" not in message_columns:
            batch_op.add_column(sa.Column("integration_account_id", sa.Integer(), nullable=True))
        if "ix_whatsapp_messages_integration_account_id" not in message_indexes:
            batch_op.create_index(
                "ix_whatsapp_messages_integration_account_id",
                ["integration_account_id"],
                unique=False,
            )
        if "fk_whatsapp_messages_integration_account_id" not in message_foreign_keys:
            batch_op.create_foreign_key(
                "fk_whatsapp_messages_integration_account_id",
                "integration_accounts",
                ["integration_account_id"],
                ["id"],
            )


def _ensure_integration_logs_column() -> None:
    columns = _column_names("integration_logs")
    indexes = _index_names("integration_logs")
    foreign_keys = _foreign_key_names("integration_logs")

    with op.batch_alter_table("integration_logs", recreate=_batch_mode()) as batch_op:
        if "integration_account_id" not in columns:
            batch_op.add_column(sa.Column("integration_account_id", sa.Integer(), nullable=True))
        if "ix_integration_logs_integration_account_id" not in indexes:
            batch_op.create_index(
                "ix_integration_logs_integration_account_id",
                ["integration_account_id"],
                unique=False,
            )
        if "fk_integration_logs_integration_account_id" not in foreign_keys:
            batch_op.create_foreign_key(
                "fk_integration_logs_integration_account_id",
                "integration_accounts",
                ["integration_account_id"],
                ["id"],
            )


def _ensure_default_company_mapping() -> None:
    bind = op.get_bind()
    users = sa.table(
        "users",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("company_id", sa.Integer()),
        sa.column("active_company_id", sa.Integer()),
    )
    companies = sa.table(
        "companies",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("status", sa.String()),
    )
    company_name = "Empresa principal"
    company_slug = _slugify(company_name)
    company_id = bind.execute(
        sa.select(companies.c.id).where(companies.c.slug == company_slug)
    ).scalar_one_or_none()
    if company_id is None:
        bind.execute(
            companies.insert().values(
                name=company_name,
                slug=company_slug,
                status="active",
            )
        )
        company_id = bind.execute(
            sa.select(companies.c.id).where(companies.c.slug == company_slug)
        ).scalar_one()

    bind.execute(
        users.update()
        .where(sa.or_(users.c.company_id.is_(None), users.c.active_company_id.is_(None)))
        .values(company_id=company_id, active_company_id=company_id)
    )


def upgrade() -> None:
    _ensure_companies()
    _ensure_users_columns()
    _ensure_integration_accounts()
    _ensure_external_sync_records()
    _ensure_appointments_columns()
    _ensure_whatsapp_columns()
    _ensure_integration_logs_column()
    _ensure_default_company_mapping()


def downgrade() -> None:
    # El downgrade no se usa en el flujo local del MVP. Mantenerlo no destructivo evita
    # romper instalaciones SQLite que requieran batch mode; las migraciones futuras deben
    # encargarse de cambios adicionales.
    pass
