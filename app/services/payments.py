from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.enums import AppointmentStatus, ChargeStatus, PaymentItemType
from app.models import Appointment, Payment, PaymentItem, User
from app.schemas.payment import PaymentCreate
from app.services.audit import log_action
from app.services.company_scope import appointment_company_clause, payment_company_clause
from app.services.commissions import rebuild_commission_for_payment
from app.services.exceptions import ConflictError, NotFoundError, ValidationError
from app.utils.dates import local_now
from app.utils.money import to_money


def _payment_query(company_id: int | None = None):
    return (
        select(Payment)
        .options(
            joinedload(Payment.appointment).joinedload(Appointment.client),
            joinedload(Payment.appointment).joinedload(Appointment.vehicle),
            joinedload(Payment.appointment).joinedload(Appointment.service),
            joinedload(Payment.appointment).joinedload(Appointment.operator),
            joinedload(Payment.cashier),
            joinedload(Payment.items),
        )
        .where(payment_company_clause(company_id))
    )


def list_payments(
    session: Session,
    *,
    target_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    company_id: int | None = None,
) -> list[Payment]:
    query = _payment_query(company_id).order_by(Payment.paid_at.desc(), Payment.id.desc())
    if target_date is not None:
        query = query.where(func.date(Payment.paid_at) == target_date)
    if date_from is not None:
        query = query.where(func.date(Payment.paid_at) >= date_from)
    if date_to is not None:
        query = query.where(func.date(Payment.paid_at) <= date_to)
    return list(session.scalars(query).unique().all())


def get_payment(session: Session, payment_id: int, *, company_id: int | None = None) -> Payment:
    payment = session.scalar(_payment_query(company_id).where(Payment.id == payment_id))
    if not payment:
        raise NotFoundError("Pago no encontrado.")
    return payment


def list_pending_charge_appointments(session: Session, *, company_id: int | None = None) -> list[Appointment]:
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
        .where(Appointment.status == AppointmentStatus.FINISHED.value)
        .where(Appointment.charge_status != ChargeStatus.PAID.value)
        .where(appointment_company_clause(company_id))
        .order_by(Appointment.scheduled_start.asc())
    )
    return list(session.scalars(query).unique().all())


def get_pending_charge_appointment(
    session: Session,
    appointment_id: int,
    *,
    company_id: int | None = None,
) -> Appointment:
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
        raise NotFoundError("Cita no encontrada para cobro.")
    if appointment.status == AppointmentStatus.CANCELLED.value:
        raise ValidationError("No puedes cobrar una cita cancelada.")
    if appointment.status != AppointmentStatus.FINISHED.value:
        raise ValidationError("Solo puedes cobrar servicios ya terminados.")
    if appointment.charge_status == ChargeStatus.PAID.value:
        raise ConflictError("La cita ya fue cobrada.")
    return appointment


def _build_ticket_number(payment: Payment) -> str:
    return f"TQ-{payment.paid_at.strftime('%Y%m%d')}-{payment.id:06d}"


def _payment_nominal_total(subtotal: Decimal, extras_total: Decimal, discount_total: Decimal) -> Decimal:
    return to_money(max(Decimal("0.00"), subtotal + extras_total - discount_total))


def create_payment(
    session: Session,
    payload: PaymentCreate,
    *,
    actor: User | None = None,
) -> Payment:
    company_id = getattr(actor, "active_company_id", None) or getattr(actor, "company_id", None)
    appointment = get_pending_charge_appointment(session, payload.appointment_id, company_id=company_id)
    subtotal = to_money(appointment.estimated_price or appointment.service.base_price or 0)

    extras_total = Decimal("0.00")
    for extra in payload.extras:
        quantity = to_money(extra.quantity)
        unit_price = to_money(extra.unit_price)
        if quantity < 0 or unit_price < 0:
            raise ValidationError("Los extras no pueden tener importes negativos.")
        extras_total = to_money(extras_total + (quantity * unit_price))

    discount_total = to_money(payload.discount_total)
    if discount_total < 0:
        raise ValidationError("El descuento no puede ser negativo.")
    if discount_total > subtotal + extras_total:
        raise ValidationError("El descuento no puede ser mayor al total del servicio.")

    total = _payment_nominal_total(subtotal, extras_total, discount_total)
    paid_at = payload.paid_at or local_now()

    payment = Payment(
        appointment_id=appointment.id,
        client_id=appointment.client_id,
        cashier_id=actor.id if actor else None,
        reference=payload.reference,
        subtotal=subtotal,
        extras_total=extras_total,
        discount_total=discount_total,
        total=total,
        payment_method=payload.payment_method.value,
        notes=payload.notes,
        paid_at=paid_at,
        created_by_user_id=actor.id if actor else None,
        updated_by_user_id=actor.id if actor else None,
    )
    session.add(payment)
    session.flush()

    payment.ticket_number = _build_ticket_number(payment)
    session.add(
        PaymentItem(
            payment_id=payment.id,
            appointment_id=appointment.id,
            service_catalog_id=appointment.service_catalog_id,
            item_type=PaymentItemType.SERVICE.value,
            description=appointment.service.name if appointment.service else "Servicio principal",
            quantity=to_money(1),
            unit_price=subtotal,
            total=subtotal,
            apply_commission=False,
        )
    )

    for extra in payload.extras:
        quantity = to_money(extra.quantity)
        unit_price = to_money(extra.unit_price)
        line_total = to_money(quantity * unit_price)
        if not extra.description.strip() or line_total <= 0:
            continue
        session.add(
            PaymentItem(
                payment_id=payment.id,
                appointment_id=appointment.id,
                service_catalog_id=None,
                item_type=PaymentItemType.EXTRA.value,
                description=extra.description.strip(),
                quantity=quantity,
                unit_price=unit_price,
                total=line_total,
                apply_commission=extra.apply_commission,
            )
        )

    appointment.charge_status = ChargeStatus.PAID.value
    appointment.paid_at = paid_at
    appointment.updated_by_user_id = actor.id if actor else None

    session.flush()
    payment = get_payment(session, payment.id, company_id=company_id)
    commission = rebuild_commission_for_payment(session, payment)

    log_action(
        session,
        actor=actor,
        action="payments.create",
        entity_type="payment",
        entity_id=payment.id,
        description=f"Pago registrado para cita {appointment.id}.",
        payload={
            "appointment_id": appointment.id,
            "ticket_number": payment.ticket_number,
            "payment_method": payment.payment_method,
            "commission_id": commission.id if commission else None,
        },
    )
    session.commit()
    return get_payment(session, payment.id, company_id=company_id)


def payment_ticket_summary(payment: Payment) -> dict:
    appointment = payment.appointment
    return {
        "payment_id": payment.id,
        "ticket_number": payment.ticket_number,
        "paid_at": payment.paid_at.isoformat(),
        "payment_method": payment.payment_method,
        "reference": payment.reference,
        "client": appointment.client.name if appointment and appointment.client else None,
        "vehicle": (
            f"{appointment.vehicle.brand} {appointment.vehicle.model}"
            if appointment and appointment.vehicle
            else None
        ),
        "service": appointment.service.name if appointment and appointment.service else None,
        "operator": appointment.operator.name if appointment and appointment.operator else None,
        "items": [
            {
                "description": item.description,
                "item_type": item.item_type,
                "quantity": str(item.quantity),
                "unit_price": str(item.unit_price),
                "total": str(item.total),
            }
            for item in payment.items
        ],
        "subtotal": str(payment.subtotal),
        "extras_total": str(payment.extras_total),
        "discount_total": str(payment.discount_total),
        "total": str(payment.total),
        "cashier": payment.cashier.name if payment.cashier else None,
    }
