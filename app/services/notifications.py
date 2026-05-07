from datetime import date, datetime, time, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.enums import NotificationType, UserRole
from app.models import Notification, User
from app.services.company_scope import notification_company_clause
from app.services.exceptions import NotFoundError, ValidationError


def _company_id_from_user(session: Session, user_id: int | None) -> int | None:
    if not user_id:
        return None
    user = session.get(User, user_id)
    return user.company_id if user else None


def create_notification(
    session: Session,
    *,
    title: str,
    message: str,
    type: str = NotificationType.INFO.value,
    user_id: int | None = None,
    appointment_id: int | None = None,
) -> Notification:
    notification = Notification(
        title=title,
        message=message,
        type=type,
        user_id=user_id,
        appointment_id=appointment_id,
        is_read=False,
    )
    session.add(notification)
    session.flush()
    return notification


def notify_roles(
    session: Session,
    *,
    roles: list[UserRole | str],
    company_id: int | None = None,
    title: str,
    message: str,
    type: str = NotificationType.INFO.value,
    appointment_id: int | None = None,
) -> list[Notification]:
    normalized = [role.value if isinstance(role, UserRole) else role for role in roles]
    query = select(User).where(User.is_active.is_(True)).where(User.role.in_(normalized))
    if company_id is not None:
        query = query.where(User.company_id == company_id)
    users = list(session.scalars(query).all())
    notifications = [
        create_notification(
            session,
            title=title,
            message=message,
            type=type,
            user_id=user.id,
            appointment_id=appointment_id,
        )
        for user in users
    ]
    if not notifications:
        notifications.append(
            create_notification(
                session,
                title=title,
                message=message,
                type=type,
                user_id=None,
                appointment_id=appointment_id,
            )
        )
    return notifications


def list_notifications(
    session: Session,
    *,
    user: User | None = None,
    limit: int = 8,
    unread_only: bool = False,
    type: str | None = None,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[Notification]:
    query = select(Notification).order_by(Notification.created_at.desc(), Notification.id.desc())
    company_id = None
    if user is not None:
        company_id = user.active_company_id or user.company_id
        if user.role == UserRole.ADMIN.value and user_id is not None:
            if user_id == 0:
                query = query.where(Notification.user_id.is_(None))
            else:
                query = query.where(Notification.user_id == user_id)
        else:
            query = query.where(or_(Notification.user_id.is_(None), Notification.user_id == user.id))
    elif user_id is not None:
        if user_id == 0:
            query = query.where(Notification.user_id.is_(None))
        else:
            query = query.where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    if type:
        query = query.where(Notification.type == type)
    if date_from is not None:
        query = query.where(Notification.created_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        query = query.where(Notification.created_at < datetime.combine(date_to + timedelta(days=1), time.min))
    query = query.where(notification_company_clause(company_id))
    if limit:
        query = query.limit(limit)
    return list(session.scalars(query).all())


def unread_notification_count(session: Session, *, user: User | None = None) -> int:
    company_id = (user.active_company_id or user.company_id) if user else None
    query = select(Notification).where(Notification.is_read.is_(False))
    if user is not None:
        query = query.where(or_(Notification.user_id.is_(None), Notification.user_id == user.id))
    query = query.where(notification_company_clause(company_id))
    return len(list(session.scalars(query).all()))


def get_notification(session: Session, notification_id: int) -> Notification:
    notification = session.get(Notification, notification_id)
    if not notification:
        raise NotFoundError("Notificacion no encontrada.")
    return notification


def mark_notification_read(session: Session, notification_id: int, *, actor: User) -> Notification:
    notification = get_notification(session, notification_id)
    if notification.user_id and actor.role != UserRole.ADMIN.value and notification.user_id != actor.id:
        raise ValidationError("No puedes modificar esta notificacion.")
    notification.is_read = True
    session.commit()
    session.refresh(notification)
    return notification


def notify_new_appointment(session: Session, appointment, *, company_id: int | None = None) -> None:
    company_id = company_id or _company_id_from_user(session, getattr(appointment, "created_by_user_id", None))
    title = "Nueva cita registrada"
    message = (
        f"{appointment.client.name if appointment.client else 'Cliente'} agendo "
        f"{appointment.service.name if appointment.service else 'un servicio'} para "
        f"{appointment.scheduled_start.strftime('%d/%m %H:%M')}."
    )
    notify_roles(
        session,
        roles=[UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.CASHIER],
        company_id=company_id,
        title=title,
        message=message,
        type=NotificationType.SUCCESS.value,
        appointment_id=appointment.id,
    )


def notify_operator_assigned(session: Session, appointment) -> None:
    if not appointment.operator_id:
        return
    create_notification(
        session,
        title="Nueva tarea asignada",
        message=(
            f"Tienes asignada la cita #{appointment.id} para "
            f"{appointment.client.name if appointment.client else 'cliente'} a las "
            f"{appointment.scheduled_start.strftime('%H:%M')}."
        ),
        type=NotificationType.INFO.value,
        user_id=appointment.operator_id,
        appointment_id=appointment.id,
    )


def notify_appointment_canceled(session: Session, appointment, *, company_id: int | None = None) -> None:
    company_id = company_id or _company_id_from_user(session, getattr(appointment, "created_by_user_id", None))
    title = "Cita cancelada"
    message = (
        f"La cita #{appointment.id} de "
        f"{appointment.client.name if appointment.client else 'cliente'} fue cancelada."
    )
    notify_roles(
        session,
        roles=[UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.CASHIER],
        company_id=company_id,
        title=title,
        message=message,
        type=NotificationType.WARNING.value,
        appointment_id=appointment.id,
    )
    if appointment.operator_id:
        create_notification(
            session,
            title=title,
            message="Tu servicio asignado fue cancelado.",
            type=NotificationType.WARNING.value,
            user_id=appointment.operator_id,
            appointment_id=appointment.id,
        )


def notify_clickup_finished(session: Session, appointment, *, company_id: int | None = None) -> None:
    company_id = company_id or _company_id_from_user(session, getattr(appointment, "created_by_user_id", None))
    notify_roles(
        session,
        roles=[UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.CASHIER],
        company_id=company_id,
        title="Servicio terminado desde ClickUp",
        message=f"La tarea externa de la cita #{appointment.id} fue marcada como terminada.",
        type=NotificationType.SUCCESS.value,
        appointment_id=appointment.id,
    )


def notify_service_issue(
    session: Session,
    appointment,
    *,
    message: str,
    user_id: int | None = None,
    company_id: int | None = None,
) -> None:
    company_id = company_id or _company_id_from_user(session, getattr(appointment, "created_by_user_id", None))
    notify_roles(
        session,
        roles=[UserRole.ADMIN, UserRole.SUPERVISOR],
        company_id=company_id,
        title="Operador reporto un problema",
        message=message,
        type=NotificationType.ERROR.value,
        appointment_id=appointment.id,
    )
    if user_id:
        create_notification(
            session,
            title="Problema reportado",
            message="Tu reporte fue enviado al supervisor.",
            type=NotificationType.INFO.value,
            user_id=user_id,
            appointment_id=appointment.id,
        )


def notify_integration_issue(
    session: Session,
    *,
    provider: str,
    message: str,
    appointment_id: int | None = None,
    company_id: int | None = None,
) -> None:
    notify_roles(
        session,
        roles=[UserRole.ADMIN, UserRole.SUPERVISOR],
        company_id=company_id,
        title=f"Fallo de integracion: {provider}",
        message=message,
        type=NotificationType.ERROR.value,
        appointment_id=appointment_id,
    )


def notify_appointment_reminder(session: Session, appointment, *, company_id: int | None = None) -> None:
    company_id = company_id or _company_id_from_user(session, getattr(appointment, "created_by_user_id", None))
    notify_roles(
        session,
        roles=[UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.CASHIER],
        company_id=company_id,
        title="Cita proxima",
        message=(
            f"La cita #{appointment.id} de "
            f"{appointment.client.name if appointment.client else 'cliente'} inicia en menos de una hora."
        ),
        type=NotificationType.INFO.value,
        appointment_id=appointment.id,
    )


def notify_operator_reminder(session: Session, appointment) -> None:
    if not appointment.operator_id:
        return
    create_notification(
        session,
        title="Servicio proximo",
        message=(
            f"Tu cita #{appointment.id} con "
            f"{appointment.client.name if appointment.client else 'cliente'} inicia en menos de 30 minutos."
        ),
        type=NotificationType.INFO.value,
        user_id=appointment.operator_id,
        appointment_id=appointment.id,
    )


def notify_service_ready_for_charge(session: Session, appointment, *, company_id: int | None = None) -> None:
    company_id = company_id or _company_id_from_user(session, getattr(appointment, "created_by_user_id", None))
    notify_roles(
        session,
        roles=[UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR],
        company_id=company_id,
        title="Servicio listo para cobro",
        message=(
            f"La cita #{appointment.id} de "
            f"{appointment.client.name if appointment.client else 'cliente'} ya puede pasar a caja."
        ),
        type=NotificationType.SUCCESS.value,
        appointment_id=appointment.id,
    )


def notify_daily_close_generated(session: Session, cash_cut, *, company_id: int | None = None) -> None:
    company_id = company_id or _company_id_from_user(session, getattr(cash_cut, "opened_by_user_id", None))
    notify_roles(
        session,
        roles=[UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR],
        company_id=company_id,
        title="Resumen diario generado",
        message=(
            f"Se genero el corte sugerido del {cash_cut.cut_date.isoformat()} "
            f"por ${cash_cut.total_sales:.2f}."
        ),
        type=NotificationType.INFO.value,
        appointment_id=None,
    )


def notify_low_stock(session: Session, product, *, company_id: int | None = None) -> None:
    company_id = company_id or _company_id_from_user(session, getattr(product, "created_by_user_id", None))
    notify_roles(
        session,
        roles=[UserRole.ADMIN, UserRole.SUPERVISOR],
        company_id=company_id,
        title="Stock bajo",
        message=(
            f"{product.name} llego a nivel minimo. Stock actual: "
            f"{product.stock} {product.unit}. Minimo: {product.minimum_stock}."
        ),
        type=NotificationType.WARNING.value,
        appointment_id=None,
    )
