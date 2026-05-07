from datetime import date, datetime, time, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.dependencies import current_company_id
from app.enums import AppointmentOrigin, AppointmentStatus, ChargeStatus, IntegrationAccountProvider, UserRole
from app.integrations.clickup.client import create_clickup_task, update_clickup_task
from app.integrations.google.calendar import (
    cancel_calendar_event,
    create_calendar_event,
    update_calendar_event,
)
from app.models import Appointment, Client, ServiceCatalog, ServiceJob, User, Vehicle
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services.audit import log_action
from app.services.company_scope import appointment_company_clause, created_by_company_clause
from app.services.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.integration_manager import get_by_id, get_default
from app.services.notifications import (
    notify_appointment_canceled,
    notify_new_appointment,
    notify_operator_assigned,
)
from app.services.whatsapp_conversations import (
    send_appointment_cancellation_message,
    send_appointment_confirmation_message,
)
from app.utils.dates import get_timezone, local_now


def list_appointments(
    session: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    include_deleted: bool = False,
    company_id: int | None = None,
) -> list[Appointment]:
    query = (
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.vehicle),
            joinedload(Appointment.service),
            joinedload(Appointment.operator),
            joinedload(Appointment.whatsapp_integration),
            joinedload(Appointment.google_calendar_integration),
            joinedload(Appointment.clickup_integration),
            joinedload(Appointment.service_job),
        )
        .where(appointment_company_clause(company_id))
        .order_by(Appointment.scheduled_start)
    )
    if not include_deleted:
        query = query.where(Appointment.deleted_at.is_(None))
    if start_date is not None:
        query = query.where(func.date(Appointment.scheduled_start) >= start_date)
    if end_date is not None:
        query = query.where(func.date(Appointment.scheduled_start) <= end_date)
    return list(session.scalars(query).unique().all())


def get_appointment(session: Session, appointment_id: int, *, company_id: int | None = None) -> Appointment:
    appointment = session.scalar(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .where(appointment_company_clause(company_id))
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.vehicle),
            joinedload(Appointment.service),
            joinedload(Appointment.operator),
            joinedload(Appointment.service_job),
            joinedload(Appointment.whatsapp_integration),
            joinedload(Appointment.google_calendar_integration),
            joinedload(Appointment.clickup_integration),
        )
    )
    if not appointment or appointment.deleted_at is not None:
        raise NotFoundError("Cita no encontrada.")
    return appointment


def _validate_schedule(scheduled_start: datetime) -> None:
    localized = scheduled_start.astimezone(get_timezone()) if scheduled_start.tzinfo else scheduled_start.replace(
        tzinfo=get_timezone()
    )
    if localized.hour < 6 or localized.hour > 22:
        raise ValidationError("La cita debe agendarse entre las 06:00 y las 22:59.")


def _validate_references(
    session: Session,
    *,
    client_id: int,
    vehicle_id: int,
    service_catalog_id: int,
    operator_id: int | None,
    company_id: int | None,
) -> tuple[Client, Vehicle, ServiceCatalog, User | None]:
    client = session.scalar(
        select(Client)
        .where(Client.id == client_id)
        .where(created_by_company_clause(Client, company_id))
    )
    if not client or client.deleted_at is not None:
        raise ValidationError("Cliente invalido.")

    vehicle = session.scalar(
        select(Vehicle)
        .where(Vehicle.id == vehicle_id)
        .where(created_by_company_clause(Vehicle, company_id))
    )
    if not vehicle or vehicle.deleted_at is not None or vehicle.client_id != client_id:
        raise ValidationError("Vehiculo invalido para el cliente seleccionado.")

    service = session.scalar(
        select(ServiceCatalog)
        .where(ServiceCatalog.id == service_catalog_id)
        .where(created_by_company_clause(ServiceCatalog, company_id))
    )
    if not service or service.deleted_at is not None:
        raise ValidationError("Servicio invalido.")

    operator = None
    if operator_id:
        operator = session.scalar(
            select(User)
            .where(User.id == operator_id)
            .where(User.is_active.is_(True))
            .where(User.company_id == company_id if company_id is not None else True)
        )
        if not operator:
            raise ValidationError("Operador invalido.")
    return client, vehicle, service, operator


def _resolve_integration_id(
    session: Session,
    *,
    actor: User | None,
    provider: str,
    selected_id: int | None,
    existing_id: int | None = None,
    preserve_existing: bool = False,
) -> int | None:
    company_id = current_company_id(actor) if actor else None
    if preserve_existing and existing_id is not None:
        return existing_id
    if selected_id:
        if not company_id:
            raise ValidationError("No fue posible determinar la empresa activa para la integracion.")
        account = get_by_id(session, company_id, selected_id)
        if account.provider != provider:
            raise ValidationError("La integracion seleccionada no coincide con el proveedor.")
        return account.id
    if existing_id is not None:
        return existing_id
    if company_id:
        default_account = get_default(session, company_id, provider)
        if default_account:
            return default_account.id
    return None


def _integration_binding_data(
    session: Session,
    *,
    actor: User | None,
    payload,
    appointment: Appointment | None = None,
) -> dict:
    return {
        "whatsapp_integration_id": _resolve_integration_id(
            session,
            actor=actor,
            provider=IntegrationAccountProvider.WHATSAPP_META.value,
            selected_id=getattr(payload, "whatsapp_integration_id", None),
            existing_id=getattr(appointment, "whatsapp_integration_id", None) if appointment else None,
            preserve_existing=appointment is not None and getattr(appointment, "whatsapp_integration_id", None) is not None,
        ),
        "google_calendar_integration_id": _resolve_integration_id(
            session,
            actor=actor,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            selected_id=getattr(payload, "google_calendar_integration_id", None),
            existing_id=getattr(appointment, "google_calendar_integration_id", None) if appointment else None,
            preserve_existing=appointment is not None and bool(getattr(appointment, "google_event_id", None)),
        ),
        "google_sheets_integration_id": getattr(payload, "google_sheets_integration_id", None)
        if getattr(payload, "google_sheets_integration_id", None) is not None
        else (getattr(appointment, "google_sheets_integration_id", None) if appointment else None),
        "clickup_integration_id": _resolve_integration_id(
            session,
            actor=actor,
            provider=IntegrationAccountProvider.CLICKUP.value,
            selected_id=getattr(payload, "clickup_integration_id", None),
            existing_id=getattr(appointment, "clickup_integration_id", None) if appointment else None,
            preserve_existing=appointment is not None and bool(getattr(appointment, "clickup_task_id", None)),
        ),
        "meta_business_integration_id": getattr(payload, "meta_business_integration_id", None)
        if getattr(payload, "meta_business_integration_id", None) is not None
        else (getattr(appointment, "meta_business_integration_id", None) if appointment else None),
    }


def _sync_creation_side_effects(session: Session, appointment: Appointment) -> None:
    google_event_id = create_calendar_event(session, appointment)
    clickup_task = create_clickup_task(session, appointment)
    if google_event_id:
        appointment.google_event_id = google_event_id
    if clickup_task:
        appointment.clickup_task_id = clickup_task.get("id")
        appointment.clickup_task_url = clickup_task.get("url")
    send_appointment_confirmation_message(session, appointment)
    session.commit()


def create_appointment(
    session: Session,
    payload: AppointmentCreate,
    *,
    actor: User | None = None,
) -> Appointment:
    company_id = current_company_id(actor) if actor else None
    _validate_schedule(payload.scheduled_start)
    client, vehicle, service, operator = _validate_references(
        session,
        client_id=payload.client_id,
        vehicle_id=payload.vehicle_id,
        service_catalog_id=payload.service_catalog_id,
        operator_id=payload.operator_id,
        company_id=company_id,
    )
    integration_data = _integration_binding_data(session, actor=actor, payload=payload)
    appointment = Appointment(
        client_id=client.id,
        vehicle_id=vehicle.id,
        service_catalog_id=service.id,
        operator_id=operator.id if operator else None,
        scheduled_start=payload.scheduled_start,
        address=payload.address,
        notes=payload.notes,
        status=payload.status.value,
        origin=payload.origin.value,
        charge_status=ChargeStatus.PENDING.value,
        estimated_price=payload.estimated_price or service.base_price,
        created_by_user_id=actor.id if actor else None,
        updated_by_user_id=actor.id if actor else None,
        **integration_data,
    )
    session.add(appointment)
    session.flush()
    session.add(ServiceJob(appointment_id=appointment.id, operator_id=appointment.operator_id))
    log_action(
        session,
        actor=actor,
        action="appointments.create",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Cita creada para {client.name}.",
        payload={
            "service_catalog_id": service.id,
            "scheduled_start": appointment.scheduled_start.isoformat(),
            "google_calendar_integration_id": appointment.google_calendar_integration_id,
            "clickup_integration_id": appointment.clickup_integration_id,
            "whatsapp_integration_id": appointment.whatsapp_integration_id,
        },
    )
    session.commit()
    appointment = get_appointment(session, appointment.id, company_id=company_id)
    notify_new_appointment(session, appointment, company_id=company_id)
    notify_operator_assigned(session, appointment)
    session.commit()
    _sync_creation_side_effects(session, appointment)
    return get_appointment(session, appointment.id, company_id=company_id)


def update_appointment(
    session: Session,
    appointment_id: int,
    payload: AppointmentUpdate,
    *,
    actor: User | None = None,
) -> Appointment:
    company_id = current_company_id(actor) if actor else None
    appointment = get_appointment(session, appointment_id, company_id=company_id)
    data = payload.model_dump(exclude_unset=True)
    previous_operator_id = appointment.operator_id

    next_start = data.get("scheduled_start", appointment.scheduled_start)
    _validate_schedule(next_start)

    client_id = data.get("client_id", appointment.client_id)
    vehicle_id = data.get("vehicle_id", appointment.vehicle_id)
    service_catalog_id = data.get("service_catalog_id", appointment.service_catalog_id)
    operator_id = data.get("operator_id", appointment.operator_id)
    _, _, service, operator = _validate_references(
        session,
        client_id=client_id,
        vehicle_id=vehicle_id,
        service_catalog_id=service_catalog_id,
        operator_id=operator_id,
        company_id=company_id,
    )

    for field, value in data.items():
        if field in {"status", "origin"} and value is not None:
            setattr(appointment, field, value.value)
            continue
        setattr(appointment, field, value)

    integration_data = _integration_binding_data(session, actor=actor, payload=payload, appointment=appointment)
    for field, value in integration_data.items():
        setattr(appointment, field, value)

    appointment.updated_by_user_id = actor.id if actor else None
    appointment.estimated_price = appointment.estimated_price or service.base_price
    if appointment.service_job:
        appointment.service_job.operator_id = operator.id if operator else None

    log_action(
        session,
        actor=actor,
        action="appointments.update",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Actualizacion de cita {appointment.id}.",
        payload={
            "google_calendar_integration_id": appointment.google_calendar_integration_id,
            "clickup_integration_id": appointment.clickup_integration_id,
            "whatsapp_integration_id": appointment.whatsapp_integration_id,
        },
    )
    session.commit()
    appointment = get_appointment(session, appointment.id, company_id=company_id)
    google_event_id = update_calendar_event(session, appointment)
    if google_event_id and google_event_id != appointment.google_event_id:
        appointment.google_event_id = google_event_id
        session.commit()
    clickup_task = update_clickup_task(session, appointment)
    if clickup_task:
        appointment.clickup_task_id = clickup_task.get("id")
        appointment.clickup_task_url = clickup_task.get("url")
        session.commit()
    if appointment.operator_id and appointment.operator_id != previous_operator_id:
        notify_operator_assigned(session, appointment)
        session.commit()
    return get_appointment(session, appointment.id, company_id=company_id)


def cancel_appointment(
    session: Session,
    appointment_id: int,
    *,
    actor: User | None = None,
    reason: str | None = None,
) -> Appointment:
    company_id = current_company_id(actor) if actor else None
    appointment = get_appointment(session, appointment_id, company_id=company_id)
    if appointment.charge_status == ChargeStatus.PAID.value and getattr(actor, "role", None) != UserRole.ADMIN.value:
        raise ValidationError("Solo un admin puede cancelar un servicio ya cobrado.")
    appointment.status = AppointmentStatus.CANCELLED.value
    appointment.canceled_at = datetime.now(timezone.utc)
    appointment.canceled_by_user_id = actor.id if actor else None
    appointment.cancellation_reason = reason or "Cancelacion manual."
    appointment.updated_by_user_id = actor.id if actor else None
    log_action(
        session,
        actor=actor,
        action="appointments.cancel",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Cancelacion de cita {appointment.id}.",
        payload={"reason": appointment.cancellation_reason},
    )
    session.commit()
    cancel_calendar_event(session, appointment)
    appointment = get_appointment(session, appointment.id, company_id=company_id)
    clickup_task = update_clickup_task(session, appointment)
    if clickup_task:
        appointment.clickup_task_id = clickup_task.get("id")
        appointment.clickup_task_url = clickup_task.get("url")
    notify_appointment_canceled(session, appointment, company_id=company_id)
    send_appointment_cancellation_message(session, appointment)
    session.commit()
    return appointment


def soft_delete_appointment(session: Session, appointment_id: int, *, actor: User | None = None) -> Appointment:
    company_id = current_company_id(actor) if actor else None
    appointment = get_appointment(session, appointment_id, company_id=company_id)
    if appointment.charge_status == ChargeStatus.PAID.value:
        raise ValidationError("No puedes dar de baja una cita ya cobrada; mantenla para historial.")
    appointment.deleted_at = datetime.now(timezone.utc)
    appointment.deleted_by_user_id = actor.id if actor else None
    appointment.delete_reason = "Eliminacion logica desde panel/API."
    appointment.status = AppointmentStatus.CANCELLED.value
    appointment.updated_by_user_id = actor.id if actor else None
    log_action(
        session,
        actor=actor,
        action="appointments.delete",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Baja logica de la cita {appointment.id}.",
    )
    session.commit()
    return appointment


def agenda_for_day(session: Session, *, target_date: date, company_id: int | None = None) -> list[Appointment]:
    return list_appointments(session, start_date=target_date, end_date=target_date, company_id=company_id)


def build_day_range(target_day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target_day, time.min).replace(tzinfo=timezone.utc)
    end = datetime.combine(target_day, time.max).replace(tzinfo=timezone.utc)
    return start, end
