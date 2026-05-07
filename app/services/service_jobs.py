from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.enums import AppointmentStatus, JobStatus, UserRole
from app.integrations.clickup.client import update_clickup_task
from app.models import Appointment, ServiceJob, User
from app.services.automations import handle_service_finished_automation
from app.services.audit import log_action
from app.services.company_scope import appointment_company_clause
from app.services.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.notifications import notify_clickup_finished, notify_service_issue
from app.utils.dates import get_timezone, local_now


def list_operator_tasks(
    session: Session,
    *,
    current_user: User,
    target_date: date | None = None,
    operator_id: int | None = None,
) -> list[Appointment]:
    company_id = current_user.active_company_id or current_user.company_id
    query = (
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.vehicle),
            joinedload(Appointment.service),
            joinedload(Appointment.operator),
            joinedload(Appointment.service_job),
        )
        .where(Appointment.deleted_at.is_(None))
        .where(Appointment.status != AppointmentStatus.CANCELLED.value)
        .where(appointment_company_clause(company_id))
        .order_by(Appointment.scheduled_start.asc())
    )
    if target_date is not None:
        query = query.where(func.date(Appointment.scheduled_start) == target_date)
    if current_user.role == UserRole.OPERATOR.value:
        query = query.where(Appointment.operator_id == current_user.id)
    elif operator_id is not None:
        query = query.where(Appointment.operator_id == operator_id)
    else:
        query = query.where(Appointment.operator_id.is_not(None))
    return list(session.scalars(query).unique().all())


def get_operator_task(session: Session, appointment_id: int, *, company_id: int | None = None) -> Appointment:
    appointment = session.scalar(
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.vehicle),
            joinedload(Appointment.service),
            joinedload(Appointment.operator),
            joinedload(Appointment.service_job),
        )
        .where(Appointment.id == appointment_id)
        .where(Appointment.deleted_at.is_(None))
        .where(appointment_company_clause(company_id))
    )
    if not appointment:
        raise NotFoundError("Cita asignada no encontrada.")
    return appointment


def _validate_operator_permission(appointment: Appointment, actor: User) -> None:
    if actor.role in {UserRole.ADMIN.value, UserRole.SUPERVISOR.value}:
        return
    if appointment.operator_id != actor.id:
        raise ValidationError("No tienes permisos para operar esta tarea.")


def _ensure_service_job(session: Session, appointment: Appointment) -> ServiceJob:
    if appointment.service_job:
        return appointment.service_job
    job = ServiceJob(appointment_id=appointment.id, operator_id=appointment.operator_id)
    session.add(job)
    session.flush()
    appointment.service_job = job
    return job


def _aware_datetime(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=get_timezone())
    return value


def start_operator_task(session: Session, appointment_id: int, *, actor: User) -> Appointment:
    company_id = actor.active_company_id or actor.company_id
    appointment = get_operator_task(session, appointment_id, company_id=company_id)
    _validate_operator_permission(appointment, actor)
    if appointment.status == AppointmentStatus.CANCELLED.value:
        raise ValidationError("No puedes iniciar una cita cancelada.")
    if appointment.status == AppointmentStatus.FINISHED.value:
        raise ConflictError("La cita ya fue terminada.")

    job = _ensure_service_job(session, appointment)
    now = local_now()
    appointment.status = AppointmentStatus.IN_PROGRESS.value
    appointment.updated_by_user_id = actor.id
    job.status = JobStatus.STARTED.value
    job.operator_id = appointment.operator_id or actor.id
    job.started_at = job.started_at or now
    job.started_by_user_id = actor.id
    log_action(
        session,
        actor=actor,
        action="service_jobs.start",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Servicio {appointment.id} iniciado.",
    )
    session.commit()
    appointment = get_operator_task(session, appointment.id, company_id=company_id)
    update_clickup_task(session, appointment)
    return get_operator_task(session, appointment.id, company_id=company_id)


def finish_operator_task(session: Session, appointment_id: int, *, actor: User) -> Appointment:
    company_id = actor.active_company_id or actor.company_id
    appointment = get_operator_task(session, appointment_id, company_id=company_id)
    _validate_operator_permission(appointment, actor)
    if appointment.status == AppointmentStatus.CANCELLED.value:
        raise ValidationError("No puedes terminar una cita cancelada.")
    if appointment.status == AppointmentStatus.FINISHED.value:
        raise ConflictError("La cita ya fue terminada.")

    job = _ensure_service_job(session, appointment)
    now = local_now()
    job.started_at = job.started_at or now
    job.ended_at = now
    job.status = JobStatus.FINISHED.value
    job.completed_by_user_id = actor.id
    elapsed_minutes = max(
        1,
        int((_aware_datetime(job.ended_at) - _aware_datetime(job.started_at)).total_seconds() // 60),
    )
    job.actual_duration_minutes = elapsed_minutes
    appointment.status = AppointmentStatus.FINISHED.value
    appointment.updated_by_user_id = actor.id
    log_action(
        session,
        actor=actor,
        action="service_jobs.finish",
        entity_type="appointment",
        entity_id=appointment.id,
        description=f"Servicio {appointment.id} terminado.",
        payload={"actual_duration_minutes": elapsed_minutes},
    )
    session.commit()
    appointment = get_operator_task(session, appointment.id, company_id=company_id)
    update_clickup_task(session, appointment)
    appointment = get_operator_task(session, appointment.id, company_id=company_id)
    handle_service_finished_automation(session, appointment)
    return get_operator_task(session, appointment.id, company_id=company_id)


def report_operator_issue(session: Session, appointment_id: int, *, actor: User, note: str) -> Appointment:
    if not note.strip():
        raise ValidationError("Describe el problema antes de enviarlo.")
    company_id = actor.active_company_id or actor.company_id
    appointment = get_operator_task(session, appointment_id, company_id=company_id)
    _validate_operator_permission(appointment, actor)
    job = _ensure_service_job(session, appointment)
    issue_note = f"[{local_now().strftime('%d/%m %H:%M')}] {actor.name}: {note.strip()}"
    job.notes = f"{job.notes}\n{issue_note}".strip() if job.notes else issue_note
    appointment.updated_by_user_id = actor.id
    notify_service_issue(
        session,
        appointment,
        message=f"{actor.name} reporto problema en la cita #{appointment.id}: {note.strip()}",
        user_id=actor.id,
        company_id=company_id,
    )
    log_action(
        session,
        actor=actor,
        action="service_jobs.issue",
        entity_type="appointment",
        entity_id=appointment.id,
        description="Problema reportado por operador.",
        payload={"note": note.strip()},
    )
    session.commit()
    return get_operator_task(session, appointment.id, company_id=company_id)


def finish_task_from_clickup(session: Session, appointment: Appointment, *, payload: dict | None = None) -> Appointment:
    company_id = appointment.operator.company_id if appointment.operator else None
    if appointment.status == AppointmentStatus.FINISHED.value and appointment.service_job:
        if appointment.service_job.status == JobStatus.FINISHED.value:
            return appointment
    job = _ensure_service_job(session, appointment)
    now = local_now()
    job.started_at = job.started_at or now
    job.ended_at = now
    job.status = JobStatus.FINISHED.value
    job.actual_duration_minutes = max(
        1,
        int((_aware_datetime(job.ended_at) - _aware_datetime(job.started_at)).total_seconds() // 60),
    )
    appointment.status = AppointmentStatus.FINISHED.value
    notify_clickup_finished(session, appointment, company_id=company_id)
    log_action(
        session,
        actor=None,
        action="clickup.sync.finished",
        entity_type="appointment",
        entity_id=appointment.id,
        description="ClickUp marco la tarea como terminada.",
        payload=payload,
    )
    session.commit()
    appointment = get_operator_task(session, appointment.id, company_id=company_id)
    handle_service_finished_automation(session, appointment)
    return get_operator_task(session, appointment.id, company_id=company_id)
