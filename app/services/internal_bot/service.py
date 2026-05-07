from __future__ import annotations

from datetime import date, time, timedelta
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.enums import (
    AppointmentOrigin,
    AppointmentStatus,
    InternalBotIntent,
    InternalBotStatus,
    UserRole,
)
from app.models import Appointment, InternalBotMessage, ServiceCatalog, User, Vehicle
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services.appointments import agenda_for_day, create_appointment, update_appointment
from app.services.cash_cuts import calculate_cash_cut_summary, get_cash_cut_by_date
from app.services.company_scope import (
    appointment_company_clause,
    created_by_company_clause,
    internal_bot_company_clause,
)
from app.services.exceptions import ServiceError, ValidationError
from app.services.internal_bot.parser import normalize_text, parse_command
from app.services.internal_bot import ai_parser
from app.services.reports import commissions_report, daily_report
from app.services.service_jobs import finish_operator_task
from app.utils.dates import combine_local_date_time, local_now


UNKNOWN_COMMAND_MESSAGE = (
    "No entendí el comando. Prueba con:\n"
    "• agenda de hoy\n• ventas de hoy\n• corte de hoy\n"
    "• servicios pendientes / en proceso / terminados\n"
    "• tareas de [operador]\n• comisiones de hoy"
)


def list_history(session: Session, *, user: User | None = None, limit: int = 50) -> list[InternalBotMessage]:
    company_id = (user.active_company_id or user.company_id) if user else None
    query = (
        select(InternalBotMessage)
        .where(internal_bot_company_clause(company_id))
        .order_by(InternalBotMessage.created_at.desc(), InternalBotMessage.id.desc())
        .limit(limit)
    )
    if user is not None and user.role != UserRole.ADMIN.value:
        query = query.where(InternalBotMessage.user_id == user.id)
    return list(session.scalars(query).all())


def _store_history(
    session: Session,
    *,
    user: User | None,
    command: str,
    response: str,
    intent: str,
    status: str,
) -> InternalBotMessage:
    message = InternalBotMessage(
        user_id=user.id if user else None,
        command=command,
        response=response,
        intent=intent,
        status=status,
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def _parse_schedule_label(value: str) -> date:
    normalized = normalize_text(value)
    today = local_now().date()
    if normalized == "hoy":
        return today
    if normalized == "manana":
        return today + timedelta(days=1)
    for pattern, builder in (
        (r"^(\d{4})-(\d{2})-(\d{2})$", lambda match: date(int(match.group(1)), int(match.group(2)), int(match.group(3)))),
        (r"^(\d{2})/(\d{2})/(\d{4})$", lambda match: date(int(match.group(3)), int(match.group(2)), int(match.group(1)))),
        (r"^(\d{2})/(\d{2})$", lambda match: date(today.year, int(match.group(2)), int(match.group(1)))),
    ):
        match = re.match(pattern, normalized)
        if not match:
            continue
        parsed = builder(match)
        if len(match.groups()) == 2 and parsed < today:
            return date(today.year + 1, parsed.month, parsed.day)
        return parsed
    raise ValidationError("No pude leer la fecha del comando.")


def _parse_time_label(value: str) -> time:
    normalized = normalize_text(value)
    match = re.match(r"^(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?$", normalized)
    if not match:
        raise ValidationError("No pude leer la hora del comando.")
    hour = int(match.group("hour"))
    minute = int(match.group("minute") or "00")
    return time(hour=hour, minute=minute)


def _find_operator_by_name(session: Session, operator_name: str, *, company_id: int | None = None) -> User:
    normalized = normalize_text(operator_name)
    operators = list(
        session.scalars(
            select(User)
            .where(User.is_active.is_(True))
            .where(User.role.in_([UserRole.OPERATOR.value, UserRole.SUPERVISOR.value]))
            .where(User.company_id == company_id if company_id is not None else True)
            .order_by(User.name.asc())
        ).all()
    )
    exact = next((user for user in operators if normalize_text(user.name) == normalized), None)
    if exact:
        return exact
    matches = [user for user in operators if normalized in normalize_text(user.name)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValidationError(f"No encontre al operador '{operator_name}'.")
    raise ValidationError(f"Hay varios operadores que coinciden con '{operator_name}'.")


def _vehicle_haystack(vehicle: Vehicle) -> str:
    parts = [
        vehicle.brand or "",
        vehicle.model or "",
        vehicle.color or "",
        vehicle.plates or "",
        vehicle.notes or "",
    ]
    return normalize_text(" ".join(parts))


def _find_vehicle_by_query(session: Session, vehicle_query: str, *, company_id: int | None = None) -> Vehicle:
    normalized = normalize_text(vehicle_query)
    vehicles = list(
        session.scalars(
            select(Vehicle)
            .options(joinedload(Vehicle.client))
            .where(Vehicle.deleted_at.is_(None))
            .where(Vehicle.is_active.is_(True))
            .where(created_by_company_clause(Vehicle, company_id))
            .order_by(Vehicle.id.desc())
        ).all()
    )
    matches = [vehicle for vehicle in vehicles if normalized in _vehicle_haystack(vehicle)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValidationError(f"No encontre un vehiculo que coincida con '{vehicle_query}'.")
    raise ValidationError(f"Hay varios vehiculos que coinciden con '{vehicle_query}'.")


def _find_service_from_details(
    session: Session,
    details: str,
    *,
    company_id: int | None = None,
) -> tuple[ServiceCatalog, str]:
    normalized_details = normalize_text(details)
    services = list(
        session.scalars(
            select(ServiceCatalog)
            .where(ServiceCatalog.deleted_at.is_(None))
            .where(ServiceCatalog.is_active.is_(True))
            .where(created_by_company_clause(ServiceCatalog, company_id))
            .order_by(func.length(ServiceCatalog.name).desc(), ServiceCatalog.name.asc())
        ).all()
    )
    for service in services:
        service_name = normalize_text(service.name)
        if normalized_details.startswith(service_name):
            vehicle_query = details[len(service.name):].strip()
            if not vehicle_query:
                raise ValidationError("Necesito identificar el vehiculo para crear la cita.")
            return service, vehicle_query

    scored_matches = []
    for service in services:
        haystack = normalize_text(" ".join([service.name, service.description or "", service.service_type]))
        if service.name and normalize_text(service.name) in normalized_details:
            score = len(normalize_text(service.name))
            scored_matches.append((score, service))
        elif any(token in haystack for token in normalized_details.split()):
            scored_matches.append((1, service))
    if not scored_matches:
        raise ValidationError("No encontre un servicio que coincida con el comando.")
    scored_matches.sort(key=lambda item: item[0], reverse=True)
    service = scored_matches[0][1]
    service_name = normalize_text(service.name)
    vehicle_query = normalized_details.replace(service_name, "", 1).strip()
    if not vehicle_query:
        raise ValidationError("Necesito identificar el vehiculo para crear la cita.")
    return service, vehicle_query


def _find_open_appointment_by_vehicle_query(
    session: Session,
    vehicle_query: str,
    *,
    company_id: int | None = None,
) -> Appointment:
    normalized = normalize_text(vehicle_query)
    appointments = list(
        session.scalars(
            select(Appointment)
            .options(
                joinedload(Appointment.client),
                joinedload(Appointment.vehicle),
                joinedload(Appointment.service),
                joinedload(Appointment.operator),
                joinedload(Appointment.service_job),
            )
            .where(Appointment.deleted_at.is_(None))
            .where(appointment_company_clause(company_id))
            .where(Appointment.status.in_([
                AppointmentStatus.PENDING.value,
                AppointmentStatus.CONFIRMED.value,
                AppointmentStatus.IN_PROGRESS.value,
            ]))
            .order_by(Appointment.scheduled_start.asc(), Appointment.id.asc())
        ).unique().all()
    )
    matches = [appointment for appointment in appointments if appointment.vehicle and normalized in _vehicle_haystack(appointment.vehicle)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValidationError(f"No encontre una cita activa para '{vehicle_query}'.")
    return matches[0]


def _format_appointments(items: list[Appointment], *, empty_message: str) -> str:
    if not items:
        return empty_message
    lines = []
    for appointment in items[:10]:
        client_name = appointment.client.name if appointment.client else "Cliente"
        vehicle_label = (
            f"{appointment.vehicle.brand} {appointment.vehicle.model}"
            if appointment.vehicle
            else f"Vehiculo {appointment.vehicle_id}"
        )
        service_name = appointment.service.name if appointment.service else "Servicio"
        operator_name = appointment.operator.name if appointment.operator else "Sin operador"
        lines.append(
            f"#{appointment.id} {appointment.scheduled_start.strftime('%H:%M')} - "
            f"{client_name} - {vehicle_label} - {service_name} - {operator_name} - {appointment.status}"
        )
    return "\n".join(lines)


def _handle_today_agenda(session: Session, *, company_id: int | None = None) -> str:
    appointments = agenda_for_day(session, target_date=local_now().date(), company_id=company_id)
    return _format_appointments(appointments, empty_message="No hay citas para hoy.")


def _handle_today_sales(session: Session, *, company_id: int | None = None) -> str:
    report = daily_report(session, target_date=local_now().date(), company_id=company_id)
    summary = report["summary"]
    return (
        f"Ventas de hoy: ${summary['total_sales']:.2f}\n"
        f"Cobrados: {summary['services_charged']}\n"
        f"Cancelados: {summary['services_canceled']}\n"
        f"Ticket promedio: ${summary['ticket_average']:.2f}"
    )


def _handle_today_cash_cut(session: Session, *, company_id: int | None = None) -> str:
    today = local_now().date()
    existing_cut = get_cash_cut_by_date(session, target_date=today, company_id=company_id)
    summary = calculate_cash_cut_summary(session, target_date=today, company_id=company_id)
    status_label = existing_cut.status if existing_cut else "sugerido"
    return (
        f"Corte de hoy ({status_label}):\n"
        f"Ventas: ${summary['total_sales']:.2f}\n"
        f"Efectivo: ${summary['cash_total']:.2f}\n"
        f"Tarjeta: ${summary['card_total']:.2f}\n"
        f"Transferencia: ${summary['transfer_total']:.2f}\n"
        f"Comisiones: ${summary['commissions_total']:.2f}\n"
        f"Utilidad estimada: ${summary['estimated_profit']:.2f}"
    )


def _handle_operator_tasks(session: Session, *, operator_name: str, company_id: int | None = None) -> str:
    operator = _find_operator_by_name(session, operator_name, company_id=company_id)
    appointments = list(
        session.scalars(
            select(Appointment)
            .options(
                joinedload(Appointment.client),
                joinedload(Appointment.vehicle),
                joinedload(Appointment.service),
                joinedload(Appointment.operator),
                joinedload(Appointment.service_job),
            )
            .where(Appointment.deleted_at.is_(None))
            .where(appointment_company_clause(company_id))
            .where(Appointment.operator_id == operator.id)
            .where(func.date(Appointment.scheduled_start) == local_now().date())
            .where(Appointment.status != AppointmentStatus.CANCELLED.value)
            .order_by(Appointment.scheduled_start.asc(), Appointment.id.asc())
        ).unique().all()
    )
    return _format_appointments(appointments, empty_message=f"{operator.name} no tiene tareas hoy.")


def _handle_services_by_status(
    session: Session,
    *,
    status: AppointmentStatus,
    empty_message: str,
    company_id: int | None = None,
) -> str:
    appointments = list(
        session.scalars(
            select(Appointment)
            .options(
                joinedload(Appointment.client),
                joinedload(Appointment.vehicle),
                joinedload(Appointment.service),
                joinedload(Appointment.operator),
            )
            .where(Appointment.deleted_at.is_(None))
            .where(appointment_company_clause(company_id))
            .where(func.date(Appointment.scheduled_start) == local_now().date())
            .where(Appointment.status == status.value)
            .order_by(Appointment.scheduled_start.asc(), Appointment.id.asc())
        ).unique().all()
    )
    return _format_appointments(appointments, empty_message=empty_message)


def _handle_today_commissions(session: Session, *, company_id: int | None = None) -> str:
    report = commissions_report(
        session,
        date_from=local_now().date(),
        date_to=local_now().date(),
        company_id=company_id,
    )
    by_operator = report["by_operator"]
    if not by_operator:
        return "No hay comisiones registradas hoy."
    lines = [f"{row['operator_name']}: ${row['total_amount']:.2f}" for row in by_operator[:10]]
    return "Comisiones de hoy:\n" + "\n".join(lines)


def _handle_operator_commissions(session: Session, *, operator_name: str, company_id: int | None = None) -> str:
    operator = _find_operator_by_name(session, operator_name, company_id=company_id)
    report = commissions_report(
        session,
        date_from=local_now().date(),
        date_to=local_now().date(),
        company_id=company_id,
        operator_id=operator.id,
    )
    summary = report["summary"]
    if not summary["commissions_count"]:
        return f"{operator.name} no tiene comisiones hoy."
    return (
        f"Comisiones de {operator.name} hoy:\n"
        f"Total: ${summary['total_amount']:.2f}\n"
        f"Registros: {summary['commissions_count']}"
    )


def _handle_reassign_operator(
    session: Session,
    *,
    actor: User,
    vehicle_query: str,
    operator_name: str,
    company_id: int | None = None,
) -> str:
    operator = _find_operator_by_name(session, operator_name, company_id=company_id)
    appointment = _find_open_appointment_by_vehicle_query(session, vehicle_query, company_id=company_id)
    updated = update_appointment(
        session,
        appointment.id,
        AppointmentUpdate(operator_id=operator.id),
        actor=actor,
    )
    return (
        f"Cita #{updated.id} reasignada a {operator.name} para "
        f"{updated.vehicle.brand} {updated.vehicle.model}."
    )


def _handle_finish_service(session: Session, *, actor: User, appointment_id: int) -> str:
    appointment = finish_operator_task(session, appointment_id, actor=actor)
    return f"Servicio #{appointment.id} marcado como terminado."


def _handle_create_appointment(
    session: Session,
    *,
    actor: User,
    schedule_label: str,
    time_label: str,
    details: str,
    company_id: int | None = None,
) -> str:
    target_date = _parse_schedule_label(schedule_label)
    target_time = _parse_time_label(time_label)
    service, vehicle_query = _find_service_from_details(session, details, company_id=company_id)
    vehicle = _find_vehicle_by_query(session, vehicle_query, company_id=company_id)
    appointment = create_appointment(
        session,
        AppointmentCreate(
            client_id=vehicle.client_id,
            vehicle_id=vehicle.id,
            service_catalog_id=service.id,
            operator_id=None,
            scheduled_start=combine_local_date_time(target_date, target_time),
            address=None,
            notes="Creada desde bot interno.",
            status=AppointmentStatus.PENDING,
            origin=AppointmentOrigin.MANUAL,
            estimated_price=service.base_price,
        ),
        actor=actor,
    )
    return (
        f"Cita #{appointment.id} creada para {vehicle.client.name if vehicle.client else 'cliente'}: "
        f"{service.name} el {appointment.scheduled_start.strftime('%d/%m/%Y %H:%M')}."
    )


def _build_context_snapshot(session: Session, *, company_id: int | None) -> str:
    """Gather a brief operational summary to give Claude context for free-form answers."""
    lines = []
    try:
        agenda = agenda_for_day(session, target_date=local_now().date(), company_id=company_id)
        lines.append(f"Citas de hoy: {len(agenda)}")
        pending   = sum(1 for a in agenda if a.status == AppointmentStatus.PENDING.value)
        in_prog   = sum(1 for a in agenda if a.status == AppointmentStatus.IN_PROGRESS.value)
        finished  = sum(1 for a in agenda if a.status == AppointmentStatus.FINISHED.value)
        cancelled = sum(1 for a in agenda if a.status == AppointmentStatus.CANCELLED.value)
        lines.append(f"  Pendientes: {pending}, En proceso: {in_prog}, Terminados: {finished}, Cancelados: {cancelled}")
    except Exception:
        pass
    try:
        report = daily_report(session, target_date=local_now().date(), company_id=company_id)
        s = report.get("summary", {})
        lines.append(f"Ventas de hoy: ${s.get('total_sales', 0):.2f}")
        lines.append(f"Servicios cobrados: {s.get('services_charged', 0)}, Pendientes de cobro: {s.get('pending_charges', 0)}")
    except Exception:
        pass
    return "\n".join(lines) if lines else "Sin datos disponibles."


def execute_command(session: Session, *, command: str, actor: User) -> dict:
    company_id = actor.active_company_id or actor.company_id

    # Try AI classification first, fall back to regex
    ai_result = ai_parser.classify_intent(command)
    if ai_result:
        parsed = ai_result
    else:
        parsed = parse_command(command)

    intent = parsed["intent"]
    params = parsed["params"]

    try:
        if intent == InternalBotIntent.GET_TODAY_AGENDA.value:
            response = _handle_today_agenda(session, company_id=company_id)
            status = InternalBotStatus.SUCCESS.value
        elif intent == InternalBotIntent.GET_TODAY_SALES.value:
            response = _handle_today_sales(session, company_id=company_id)
            status = InternalBotStatus.SUCCESS.value
        elif intent == InternalBotIntent.GET_TODAY_CASH_CUT.value:
            response = _handle_today_cash_cut(session, company_id=company_id)
            status = InternalBotStatus.SUCCESS.value
        elif intent == InternalBotIntent.GET_OPERATOR_TASKS.value:
            response = _handle_operator_tasks(session, operator_name=params["operator_name"], company_id=company_id)
            status = InternalBotStatus.SUCCESS.value
        elif intent == InternalBotIntent.GET_PENDING_SERVICES.value:
            response = _handle_services_by_status(
                session,
                status=AppointmentStatus.PENDING,
                empty_message="No hay servicios pendientes hoy.",
                company_id=company_id,
            )
            status = InternalBotStatus.SUCCESS.value
        elif intent == InternalBotIntent.GET_IN_PROGRESS_SERVICES.value:
            response = _handle_services_by_status(
                session,
                status=AppointmentStatus.IN_PROGRESS,
                empty_message="No hay servicios en proceso.",
                company_id=company_id,
            )
            status = InternalBotStatus.SUCCESS.value
        elif intent == InternalBotIntent.GET_FINISHED_SERVICES.value:
            response = _handle_services_by_status(
                session,
                status=AppointmentStatus.FINISHED,
                empty_message="No hay servicios terminados hoy.",
                company_id=company_id,
            )
            status = InternalBotStatus.SUCCESS.value
        elif intent == InternalBotIntent.GET_TODAY_COMMISSIONS.value:
            response = _handle_today_commissions(session, company_id=company_id)
            status = InternalBotStatus.SUCCESS.value
        elif intent == InternalBotIntent.GET_OPERATOR_COMMISSIONS.value:
            response = _handle_operator_commissions(
                session,
                operator_name=params["operator_name"],
                company_id=company_id,
            )
            status = InternalBotStatus.SUCCESS.value
        elif intent == InternalBotIntent.REASSIGN_OPERATOR.value:
            response = _handle_reassign_operator(session, actor=actor, company_id=company_id, **params)
            status = InternalBotStatus.SUCCESS.value
        elif intent == InternalBotIntent.FINISH_SERVICE.value:
            response = _handle_finish_service(session, actor=actor, **params)
            status = InternalBotStatus.SUCCESS.value
        elif intent == InternalBotIntent.CREATE_APPOINTMENT.value:
            response = _handle_create_appointment(session, actor=actor, company_id=company_id, **params)
            status = InternalBotStatus.SUCCESS.value
        else:
            # Try free-form AI answer before giving up
            if ai_parser.is_available():
                context = _build_context_snapshot(session, company_id=company_id)
                ai_answer = ai_parser.answer_freeform(command, context)
                if ai_answer:
                    response = ai_answer
                    status = InternalBotStatus.SUCCESS.value
                else:
                    response = UNKNOWN_COMMAND_MESSAGE
                    status = InternalBotStatus.UNKNOWN.value
            else:
                response = UNKNOWN_COMMAND_MESSAGE
                status = InternalBotStatus.UNKNOWN.value
            intent = InternalBotIntent.UNKNOWN.value
    except ServiceError as exc:
        response = str(exc)
        status = InternalBotStatus.ERROR.value
    except Exception as exc:  # pragma: no cover - defensive branch
        response = f"No pude completar el comando: {exc}"
        status = InternalBotStatus.ERROR.value

    history = _store_history(
        session,
        user=actor,
        command=command,
        response=response,
        intent=intent,
        status=status,
    )
    return {
        "id": history.id,
        "command": history.command,
        "response": history.response,
        "intent": history.intent,
        "status": history.status,
        "created_at": history.created_at,
    }
