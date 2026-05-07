from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.enums import AppointmentStatus, CashCutStatus, PaymentMethod
from app.models import Appointment, CashCut, Commission, InventoryMovement, Payment, User
from app.services.audit import log_action
from app.services.company_scope import appointment_company_clause, cash_cut_company_clause, payment_company_clause
from app.utils.dates import local_now
from app.utils.money import to_money


def calculate_cash_cut_summary(session: Session, *, target_date: date, company_id: int | None = None) -> dict:
    payments = list(
        session.scalars(
            select(Payment)
            .options(joinedload(Payment.appointment))
            .where(payment_company_clause(company_id))
            .where(func.date(Payment.paid_at) == target_date)
        ).all()
    )

    non_courtesy_sales = to_money(
        sum(payment.total for payment in payments if payment.payment_method != PaymentMethod.COURTESY.value)
    )
    cash_total = to_money(
        sum(payment.total for payment in payments if payment.payment_method == PaymentMethod.CASH.value)
    )
    card_total = to_money(
        sum(payment.total for payment in payments if payment.payment_method == PaymentMethod.CARD.value)
    )
    transfer_total = to_money(
        sum(payment.total for payment in payments if payment.payment_method == PaymentMethod.TRANSFER.value)
    )
    courtesy_total = to_money(
        sum(payment.total for payment in payments if payment.payment_method == PaymentMethod.COURTESY.value)
    )
    discounts_total = to_money(sum(payment.discount_total for payment in payments))
    paid_appointment_ids = {payment.appointment_id for payment in payments if payment.appointment_id}
    services_charged = len(paid_appointment_ids)

    services_completed = (
        session.scalar(
            select(func.count(Appointment.id))
            .where(appointment_company_clause(company_id))
            .where(func.date(Appointment.paid_at) == target_date)
            .where(Appointment.status == AppointmentStatus.FINISHED.value)
        )
        or 0
    )
    services_canceled = (
        session.scalar(
            select(func.count(Appointment.id))
            .where(appointment_company_clause(company_id))
            .where(
                (func.date(Appointment.canceled_at) == target_date)
                | (
                    (Appointment.canceled_at.is_(None))
                    & (func.date(Appointment.scheduled_start) == target_date)
                    & (Appointment.status == AppointmentStatus.CANCELLED.value)
                )
            )
        )
        or 0
    )
    commissions_total = to_money(
        session.scalar(
            select(func.coalesce(func.sum(Commission.total_amount), 0))
            .join(Payment, Payment.id == Commission.payment_id, isouter=True)
            .where(payment_company_clause(company_id))
            .where(Commission.period_date == target_date)
        )
        or 0
    )
    if paid_appointment_ids:
        cost_total = to_money(
            session.scalar(
                select(func.coalesce(func.sum(InventoryMovement.quantity * InventoryMovement.unit_cost), 0))
                .where(InventoryMovement.appointment_id.in_(paid_appointment_ids))
                .where(func.date(InventoryMovement.created_at) == target_date)
            )
            or 0
        )
    else:
        cost_total = to_money(0)
    estimated_profit = to_money(non_courtesy_sales - commissions_total - cost_total)

    return {
        "cut_date": target_date,
        "total_sales": non_courtesy_sales,
        "cash_total": cash_total,
        "card_total": card_total,
        "transfer_total": transfer_total,
        "courtesy_total": courtesy_total,
        "discounts_total": discounts_total,
        "commissions_total": commissions_total,
        "cost_total": cost_total,
        "estimated_profit": estimated_profit,
        "services_completed": services_completed,
        "services_charged": services_charged,
        "services_canceled": services_canceled,
        "expected_cash_total": cash_total,
        "expected_non_cash_total": to_money(card_total + transfer_total),
        "cash_difference": to_money(0),
        "non_cash_difference": to_money(0),
    }


def list_cash_cuts(session: Session, *, company_id: int | None = None) -> list[CashCut]:
    return list(
        session.scalars(
            select(CashCut)
            .options(joinedload(CashCut.opened_by), joinedload(CashCut.closed_by))
            .where(cash_cut_company_clause(company_id))
            .order_by(CashCut.cut_date.desc(), CashCut.id.desc())
        ).all()
    )


def get_cash_cut_by_date(session: Session, *, target_date: date, company_id: int | None = None) -> CashCut | None:
    return session.scalar(
        select(CashCut)
        .options(joinedload(CashCut.opened_by), joinedload(CashCut.closed_by))
        .where(cash_cut_company_clause(company_id))
        .where(CashCut.cut_date == target_date)
    )


def create_or_refresh_cash_cut(
    session: Session,
    *,
    target_date: date,
    actor: User | None = None,
    close_cut: bool = False,
    notes: str | None = None,
    company_id: int | None = None,
) -> CashCut:
    effective_company_id = company_id or getattr(actor, "active_company_id", None) or getattr(actor, "company_id", None)
    summary = calculate_cash_cut_summary(session, target_date=target_date, company_id=effective_company_id)
    cash_cut = get_cash_cut_by_date(session, target_date=target_date, company_id=effective_company_id)
    now = local_now()

    if cash_cut is None:
        cash_cut = CashCut(
            cut_date=target_date,
            cashier_id=actor.id if actor else None,
            opened_by_user_id=actor.id if actor else None,
            opened_at=now,
            status=CashCutStatus.OPEN.value,
        )
        session.add(cash_cut)

    for field, value in summary.items():
        setattr(cash_cut, field, value)
    if notes is not None:
        cash_cut.notes = notes
    if close_cut:
        cash_cut.status = CashCutStatus.CLOSED.value
        cash_cut.closed_by_user_id = actor.id if actor else cash_cut.closed_by_user_id
        cash_cut.closed_at = now
    elif cash_cut.opened_at is None:
        cash_cut.opened_at = now

    session.flush()
    log_action(
        session,
        actor=actor,
        action="cash_cuts.generate",
        entity_type="cash_cut",
        entity_id=cash_cut.id,
        description=f"Corte actualizado para {target_date.isoformat()}.",
        payload={"close_cut": close_cut, "company_id": effective_company_id},
    )
    session.commit()
    session.refresh(cash_cut)
    return get_cash_cut_by_date(session, target_date=target_date, company_id=effective_company_id) or cash_cut
