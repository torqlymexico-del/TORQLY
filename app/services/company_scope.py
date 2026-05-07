from __future__ import annotations

from sqlalchemy import Select, false, or_, select, true

from app.models import (
    Appointment,
    CashCut,
    Client,
    Commission,
    InternalBotMessage,
    Notification,
    Payment,
    ServiceCatalog,
    User,
    Vehicle,
    WhatsAppConversation,
)


def company_user_ids(company_id: int | None):
    if company_id is None:
        return select(User.id).where(false())
    return select(User.id).where(User.company_id == company_id)


def company_client_ids(company_id: int | None):
    user_ids = company_user_ids(company_id)
    return select(Client.id).where(Client.created_by_user_id.in_(user_ids))


def company_vehicle_ids(company_id: int | None):
    user_ids = company_user_ids(company_id)
    return select(Vehicle.id).where(
        or_(
            Vehicle.created_by_user_id.in_(user_ids),
            Vehicle.client_id.in_(company_client_ids(company_id)),
        )
    )


def company_service_ids(company_id: int | None):
    user_ids = company_user_ids(company_id)
    return select(ServiceCatalog.id).where(ServiceCatalog.created_by_user_id.in_(user_ids))


def company_appointment_ids(company_id: int | None):
    user_ids = company_user_ids(company_id)
    return select(Appointment.id).where(
        or_(
            Appointment.created_by_user_id.in_(user_ids),
            Appointment.client_id.in_(company_client_ids(company_id)),
            Appointment.vehicle_id.in_(company_vehicle_ids(company_id)),
            Appointment.service_catalog_id.in_(company_service_ids(company_id)),
            Appointment.operator_id.in_(user_ids),
        )
    )


def company_payment_ids(company_id: int | None):
    user_ids = company_user_ids(company_id)
    return select(Payment.id).where(
        or_(
            Payment.created_by_user_id.in_(user_ids),
            Payment.cashier_id.in_(user_ids),
            Payment.appointment_id.in_(company_appointment_ids(company_id)),
        )
    )


def created_by_company_clause(model, company_id: int | None):
    if company_id is None:
        return true()
    created_by_column = getattr(model, "created_by_user_id", None)
    if created_by_column is None:
        return true()
    return created_by_column.in_(company_user_ids(company_id))


def appointment_company_clause(company_id: int | None):
    if company_id is None:
        return true()
    return Appointment.id.in_(company_appointment_ids(company_id))


def payment_company_clause(company_id: int | None):
    if company_id is None:
        return true()
    return Payment.id.in_(company_payment_ids(company_id))


def commission_company_clause(company_id: int | None):
    if company_id is None:
        return true()
    user_ids = company_user_ids(company_id)
    return or_(
        Commission.user_id.in_(user_ids),
        Commission.appointment_id.in_(company_appointment_ids(company_id)),
        Commission.payment_id.in_(company_payment_ids(company_id)),
    )


def cash_cut_company_clause(company_id: int | None):
    if company_id is None:
        return true()
    user_ids = company_user_ids(company_id)
    return or_(
        CashCut.cashier_id.in_(user_ids),
        CashCut.opened_by_user_id.in_(user_ids),
        CashCut.closed_by_user_id.in_(user_ids),
    )


def notification_company_clause(company_id: int | None):
    if company_id is None:
        return true()
    user_ids = company_user_ids(company_id)
    return or_(
        Notification.user_id.in_(user_ids),
        Notification.appointment_id.in_(company_appointment_ids(company_id)),
    )


def internal_bot_company_clause(company_id: int | None):
    if company_id is None:
        return true()
    return InternalBotMessage.user_id.in_(company_user_ids(company_id))


def whatsapp_conversation_company_clause(company_id: int | None):
    if company_id is None:
        return true()
    user_ids = company_user_ids(company_id)
    return or_(
        WhatsAppConversation.assigned_admin_user_id.in_(user_ids),
        WhatsAppConversation.client_id.in_(company_client_ids(company_id)),
    )


def apply_clause(query: Select, clause):
    return query.where(clause)
