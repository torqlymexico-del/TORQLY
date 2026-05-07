"""Initial Torqly schema.

Revision ID: 20260424_0001
Revises:
Create Date: 2026-04-24 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=25), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("weekly_salary", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("commission_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=25), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delete_reason", sa.String(length=255), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deleted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_clients_id", "clients", ["id"], unique=False)
    op.create_index("ix_clients_name", "clients", ["name"], unique=False)
    op.create_index("ix_clients_phone", "clients", ["phone"], unique=False)

    op.create_table(
        "services_catalog",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("service_type", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delete_reason", sa.String(length=255), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deleted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_services_catalog_id", "services_catalog", ["id"], unique=False)
    op.create_index("ix_services_catalog_name", "services_catalog", ["name"], unique=True)

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("brand", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("color", sa.String(length=50), nullable=True),
        sa.Column("plates", sa.String(length=20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delete_reason", sa.String(length=255), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deleted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_vehicles_id", "vehicles", ["id"], unique=False)
    op.create_index("ix_vehicles_client_id", "vehicles", ["client_id"], unique=False)
    op.create_index("ix_vehicles_plates", "vehicles", ["plates"], unique=False)

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("service_catalog_id", sa.Integer(), sa.ForeignKey("services_catalog.id"), nullable=False),
        sa.Column("operator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("origin", sa.String(length=30), nullable=False),
        sa.Column("estimated_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("google_event_id", sa.String(length=255), nullable=True),
        sa.Column("clickup_task_id", sa.String(length=255), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delete_reason", sa.String(length=255), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deleted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_appointments_id", "appointments", ["id"], unique=False)
    op.create_index("ix_appointments_client_id", "appointments", ["client_id"], unique=False)
    op.create_index("ix_appointments_vehicle_id", "appointments", ["vehicle_id"], unique=False)
    op.create_index("ix_appointments_service_catalog_id", "appointments", ["service_catalog_id"], unique=False)
    op.create_index("ix_appointments_operator_id", "appointments", ["operator_id"], unique=False)
    op.create_index("ix_appointments_scheduled_start", "appointments", ["scheduled_start"], unique=False)

    op.create_table(
        "service_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=False),
        sa.Column("operator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("completed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("appointment_id"),
    )
    op.create_index("ix_service_jobs_id", "service_jobs", ["id"], unique=False)
    op.create_index("ix_service_jobs_appointment_id", "service_jobs", ["appointment_id"], unique=True)
    op.create_index("ix_service_jobs_operator_id", "service_jobs", ["operator_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("cashier_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("extras_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("discount_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("payment_method", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deleted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_payments_id", "payments", ["id"], unique=False)
    op.create_index("ix_payments_appointment_id", "payments", ["appointment_id"], unique=False)
    op.create_index("ix_payments_client_id", "payments", ["client_id"], unique=False)
    op.create_index("ix_payments_cashier_id", "payments", ["cashier_id"], unique=False)

    op.create_table(
        "payment_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=True),
        sa.Column("service_catalog_id", sa.Integer(), sa.ForeignKey("services_catalog.id"), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_payment_items_id", "payment_items", ["id"], unique=False)
    op.create_index("ix_payment_items_payment_id", "payment_items", ["payment_id"], unique=False)

    op.create_table(
        "commissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=True),
        sa.Column("service_job_id", sa.Integer(), sa.ForeignKey("service_jobs.id"), nullable=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("base_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("extra_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("calculation_note", sa.String(length=255), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_commissions_id", "commissions", ["id"], unique=False)
    op.create_index("ix_commissions_user_id", "commissions", ["user_id"], unique=False)
    op.create_index("ix_commissions_appointment_id", "commissions", ["appointment_id"], unique=False)
    op.create_index("ix_commissions_service_job_id", "commissions", ["service_job_id"], unique=False)
    op.create_index("ix_commissions_payment_id", "commissions", ["payment_id"], unique=False)
    op.create_index("ix_commissions_period_date", "commissions", ["period_date"], unique=False)

    op.create_table(
        "cash_cuts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cut_date", sa.Date(), nullable=False),
        sa.Column("cashier_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("total_sales", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("cash_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("card_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("transfer_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("courtesy_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("discounts_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("commissions_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("estimated_profit", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("services_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("services_canceled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_cash_cuts_id", "cash_cuts", ["id"], unique=False)
    op.create_index("ix_cash_cuts_cut_date", "cash_cuts", ["cut_date"], unique=False)
    op.create_index("ix_cash_cuts_cashier_id", "cash_cuts", ["cashier_id"], unique=False)

    op.create_table(
        "inventory_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("stock", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("minimum_stock", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delete_reason", sa.String(length=255), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deleted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_inventory_products_id", "inventory_products", ["id"], unique=False)
    op.create_index("ix_inventory_products_name", "inventory_products", ["name"], unique=False)
    op.create_index("ix_inventory_products_category", "inventory_products", ["category"], unique=False)

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("inventory_products.id"), nullable=False),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=True),
        sa.Column("service_job_id", sa.Integer(), sa.ForeignKey("service_jobs.id"), nullable=True),
        sa.Column("movement_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deleted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_inventory_movements_id", "inventory_movements", ["id"], unique=False)
    op.create_index("ix_inventory_movements_product_id", "inventory_movements", ["product_id"], unique=False)
    op.create_index("ix_inventory_movements_appointment_id", "inventory_movements", ["appointment_id"], unique=False)
    op.create_index("ix_inventory_movements_service_job_id", "inventory_movements", ["service_job_id"], unique=False)

    op.create_table(
        "whatsapp_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("phone", sa.String(length=25), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("mode", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_admin_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_whatsapp_conversations_id", "whatsapp_conversations", ["id"], unique=False)
    op.create_index("ix_whatsapp_conversations_client_id", "whatsapp_conversations", ["client_id"], unique=False)
    op.create_index("ix_whatsapp_conversations_phone", "whatsapp_conversations", ["phone"], unique=False)

    op.create_table(
        "whatsapp_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("whatsapp_conversations.id"), nullable=False),
        sa.Column("direction", sa.String(length=30), nullable=False),
        sa.Column("message_type", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_whatsapp_messages_id", "whatsapp_messages", ["id"], unique=False)
    op.create_index("ix_whatsapp_messages_conversation_id", "whatsapp_messages", ["conversation_id"], unique=False)
    op.create_index("ix_whatsapp_messages_external_message_id", "whatsapp_messages", ["external_message_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"], unique=False)
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"], unique=False)
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"], unique=False)

    op.create_table(
        "integration_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=True),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_integration_logs_id", "integration_logs", ["id"], unique=False)
    op.create_index("ix_integration_logs_event_type", "integration_logs", ["event_type"], unique=False)
    op.create_index("ix_integration_logs_entity_type", "integration_logs", ["entity_type"], unique=False)
    op.create_index("ix_integration_logs_entity_id", "integration_logs", ["entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_integration_logs_entity_id", table_name="integration_logs")
    op.drop_index("ix_integration_logs_entity_type", table_name="integration_logs")
    op.drop_index("ix_integration_logs_event_type", table_name="integration_logs")
    op.drop_index("ix_integration_logs_id", table_name="integration_logs")
    op.drop_table("integration_logs")

    op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_whatsapp_messages_external_message_id", table_name="whatsapp_messages")
    op.drop_index("ix_whatsapp_messages_conversation_id", table_name="whatsapp_messages")
    op.drop_index("ix_whatsapp_messages_id", table_name="whatsapp_messages")
    op.drop_table("whatsapp_messages")

    op.drop_index("ix_whatsapp_conversations_phone", table_name="whatsapp_conversations")
    op.drop_index("ix_whatsapp_conversations_client_id", table_name="whatsapp_conversations")
    op.drop_index("ix_whatsapp_conversations_id", table_name="whatsapp_conversations")
    op.drop_table("whatsapp_conversations")

    op.drop_index("ix_inventory_movements_service_job_id", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_appointment_id", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_product_id", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_id", table_name="inventory_movements")
    op.drop_table("inventory_movements")

    op.drop_index("ix_inventory_products_category", table_name="inventory_products")
    op.drop_index("ix_inventory_products_name", table_name="inventory_products")
    op.drop_index("ix_inventory_products_id", table_name="inventory_products")
    op.drop_table("inventory_products")

    op.drop_index("ix_cash_cuts_cashier_id", table_name="cash_cuts")
    op.drop_index("ix_cash_cuts_cut_date", table_name="cash_cuts")
    op.drop_index("ix_cash_cuts_id", table_name="cash_cuts")
    op.drop_table("cash_cuts")

    op.drop_index("ix_commissions_period_date", table_name="commissions")
    op.drop_index("ix_commissions_payment_id", table_name="commissions")
    op.drop_index("ix_commissions_service_job_id", table_name="commissions")
    op.drop_index("ix_commissions_appointment_id", table_name="commissions")
    op.drop_index("ix_commissions_user_id", table_name="commissions")
    op.drop_index("ix_commissions_id", table_name="commissions")
    op.drop_table("commissions")

    op.drop_index("ix_payment_items_payment_id", table_name="payment_items")
    op.drop_index("ix_payment_items_id", table_name="payment_items")
    op.drop_table("payment_items")

    op.drop_index("ix_payments_cashier_id", table_name="payments")
    op.drop_index("ix_payments_client_id", table_name="payments")
    op.drop_index("ix_payments_appointment_id", table_name="payments")
    op.drop_index("ix_payments_id", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_service_jobs_operator_id", table_name="service_jobs")
    op.drop_index("ix_service_jobs_appointment_id", table_name="service_jobs")
    op.drop_index("ix_service_jobs_id", table_name="service_jobs")
    op.drop_table("service_jobs")

    op.drop_index("ix_appointments_scheduled_start", table_name="appointments")
    op.drop_index("ix_appointments_operator_id", table_name="appointments")
    op.drop_index("ix_appointments_service_catalog_id", table_name="appointments")
    op.drop_index("ix_appointments_vehicle_id", table_name="appointments")
    op.drop_index("ix_appointments_client_id", table_name="appointments")
    op.drop_index("ix_appointments_id", table_name="appointments")
    op.drop_table("appointments")

    op.drop_index("ix_vehicles_plates", table_name="vehicles")
    op.drop_index("ix_vehicles_client_id", table_name="vehicles")
    op.drop_index("ix_vehicles_id", table_name="vehicles")
    op.drop_table("vehicles")

    op.drop_index("ix_services_catalog_name", table_name="services_catalog")
    op.drop_index("ix_services_catalog_id", table_name="services_catalog")
    op.drop_table("services_catalog")

    op.drop_index("ix_clients_phone", table_name="clients")
    op.drop_index("ix_clients_name", table_name="clients")
    op.drop_index("ix_clients_id", table_name="clients")
    op.drop_table("clients")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
