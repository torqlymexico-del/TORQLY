from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Appointment, Commission, Payment
from app.services.company_scope import commission_company_clause
from app.utils.money import to_money


def _commission_period_label(period_date: date, *, period: str) -> str:
    if period == "weekly":
        start = period_date - timedelta(days=period_date.weekday())
        end = start + timedelta(days=6)
        return f"{start.isoformat()} a {end.isoformat()}"
    return period_date.isoformat()


def rebuild_commission_for_payment(session: Session, payment: Payment) -> Commission | None:
    existing_records = list(
        session.scalars(select(Commission).where(Commission.payment_id == payment.id)).all()
    )
    for record in existing_records:
        session.delete(record)
    session.flush()

    appointment = payment.appointment
    if not appointment:
        return None

    operator = appointment.operator
    if operator is None and appointment.service_job and appointment.service_job.operator_id:
        operator = appointment.service_job.operator
    if operator is None:
        return None

    percentage = to_money(operator.commission_percentage) / to_money(100)
    if percentage <= 0:
        return None

    commissionable_extra_total = to_money(
        sum(
            item.total
            for item in payment.items
            if item.item_type == "extra" and item.apply_commission
        )
    )
    base_amount = to_money(payment.subtotal * percentage)
    extra_amount = to_money(commissionable_extra_total * percentage)
    total_amount = to_money(base_amount + extra_amount)

    commission = Commission(
        user_id=operator.id,
        appointment_id=appointment.id,
        service_job_id=appointment.service_job.id if appointment.service_job else None,
        payment_id=payment.id,
        base_amount=base_amount,
        extra_amount=extra_amount,
        total_amount=total_amount,
        calculation_note=(
            f"Porcentaje {operator.commission_percentage}% aplicado a subtotal "
            f"{payment.subtotal} y extras comisionables {commissionable_extra_total}."
        ),
        calculated_at=payment.paid_at,
        period_date=payment.paid_at.date(),
    )
    session.add(commission)
    session.flush()
    return commission


def list_commissions(
    session: Session,
    *,
    company_id: int | None = None,
    operator_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[Commission]:
    query = (
        select(Commission)
        .options(joinedload(Commission.user), joinedload(Commission.payment))
        .where(commission_company_clause(company_id))
        .order_by(Commission.period_date.desc(), Commission.id.desc())
    )
    if operator_id is not None:
        query = query.where(Commission.user_id == operator_id)
    if date_from is not None:
        query = query.where(Commission.period_date >= date_from)
    if date_to is not None:
        query = query.where(Commission.period_date <= date_to)
    return list(session.scalars(query).unique().all())


def summarize_commissions_by_operator(
    session: Session,
    *,
    company_id: int | None = None,
    operator_id: int,
    date_from: date,
    date_to: date,
    period: str = "daily",
) -> list[dict]:
    commissions = list_commissions(
        session,
        company_id=company_id,
        operator_id=operator_id,
        date_from=date_from,
        date_to=date_to,
    )
    grouped: dict[str, dict] = {}
    for commission in commissions:
        if commission.period_date is None:
            continue
        label = _commission_period_label(commission.period_date, period=period)
        bucket = grouped.setdefault(
            label,
            {
                "operator_id": operator_id,
                "operator_name": commission.user.name if commission.user else f"Operador {operator_id}",
                "period_label": label,
                "commission_count": 0,
                "base_amount": to_money(0),
                "extra_amount": to_money(0),
                "total_amount": to_money(0),
            },
        )
        bucket["commission_count"] += 1
        bucket["base_amount"] = to_money(bucket["base_amount"] + commission.base_amount)
        bucket["extra_amount"] = to_money(bucket["extra_amount"] + commission.extra_amount)
        bucket["total_amount"] = to_money(bucket["total_amount"] + commission.total_amount)
    return list(grouped.values())
