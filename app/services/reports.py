from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Appointment, Commission, Payment, ServiceJob
from app.services.cash_cuts import calculate_cash_cut_summary
from app.services.company_scope import (
    appointment_company_clause,
    commission_company_clause,
    payment_company_clause,
)
from app.services.payments import list_pending_charge_appointments
from app.utils.money import to_money


def _normalize_window(
    *,
    date_from: date | None,
    date_to: date | None,
    default_days: int = 0,
) -> tuple[date, date]:
    if date_from and date_to:
        if date_from > date_to:
            return date_to, date_from
        return date_from, date_to
    if date_from:
        return date_from, date_from
    if date_to:
        return date_to, date_to
    end = date.today()
    start = end - timedelta(days=default_days)
    return start, end


def _appointment_query():
    return (
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.vehicle),
            joinedload(Appointment.service),
            joinedload(Appointment.operator),
            joinedload(Appointment.service_job),
        )
        .where(Appointment.deleted_at.is_(None))
    )


def _payment_query():
    return (
        select(Payment)
        .options(
            joinedload(Payment.client),
            joinedload(Payment.cashier),
            joinedload(Payment.items),
            joinedload(Payment.appointment).joinedload(Appointment.client),
            joinedload(Payment.appointment).joinedload(Appointment.vehicle),
            joinedload(Payment.appointment).joinedload(Appointment.service),
            joinedload(Payment.appointment).joinedload(Appointment.operator),
            joinedload(Payment.appointment).joinedload(Appointment.service_job),
        )
    )


def _commission_query():
    return (
        select(Commission)
        .options(
            joinedload(Commission.user),
            joinedload(Commission.payment).joinedload(Payment.appointment).joinedload(Appointment.service),
        )
    )


def _load_filtered_appointments(
    session: Session,
    *,
    date_from: date,
    date_to: date,
    company_id: int | None = None,
    operator_id: int | None = None,
    service_catalog_id: int | None = None,
) -> list[Appointment]:
    query = (
        _appointment_query()
        .where(appointment_company_clause(company_id))
        .where(func.date(Appointment.scheduled_start) >= date_from)
        .where(func.date(Appointment.scheduled_start) <= date_to)
        .order_by(Appointment.scheduled_start.asc(), Appointment.id.asc())
    )
    if operator_id is not None:
        query = query.where(Appointment.operator_id == operator_id)
    if service_catalog_id is not None:
        query = query.where(Appointment.service_catalog_id == service_catalog_id)
    return list(session.scalars(query).unique().all())


def _load_filtered_payments(
    session: Session,
    *,
    date_from: date,
    date_to: date,
    company_id: int | None = None,
    operator_id: int | None = None,
    service_catalog_id: int | None = None,
    payment_method: str | None = None,
) -> list[Payment]:
    query = (
        _payment_query()
        .where(payment_company_clause(company_id))
        .where(func.date(Payment.paid_at) >= date_from)
        .where(func.date(Payment.paid_at) <= date_to)
        .order_by(Payment.paid_at.asc(), Payment.id.asc())
    )
    if payment_method:
        query = query.where(Payment.payment_method == payment_method)
    if operator_id is not None:
        query = query.where(Appointment.operator_id == operator_id)
    if service_catalog_id is not None:
        query = query.where(Appointment.service_catalog_id == service_catalog_id)
    query = query.join(Payment.appointment, isouter=True)
    return list(session.scalars(query).unique().all())


def _load_filtered_commissions(
    session: Session,
    *,
    date_from: date,
    date_to: date,
    company_id: int | None = None,
    operator_id: int | None = None,
) -> list[Commission]:
    query = (
        _commission_query()
        .where(commission_company_clause(company_id))
        .where(Commission.period_date.is_not(None))
        .where(Commission.period_date >= date_from)
        .where(Commission.period_date <= date_to)
        .order_by(Commission.period_date.asc(), Commission.id.asc())
    )
    if operator_id is not None:
        query = query.where(Commission.user_id == operator_id)
    return list(session.scalars(query).unique().all())


def _sales_by_day(payments: list[Payment]) -> list[dict]:
    grouped: dict[date, dict] = {}
    for payment in payments:
        day = payment.paid_at.date()
        bucket = grouped.setdefault(
            day,
            {"date": day.isoformat(), "total_sales": to_money(0), "transactions": 0},
        )
        bucket["total_sales"] = to_money(bucket["total_sales"] + payment.total)
        bucket["transactions"] += 1
    rows = []
    for _, bucket in sorted(grouped.items(), key=lambda item: item[0]):
        transactions = bucket["transactions"]
        average_ticket = to_money(bucket["total_sales"] / transactions) if transactions else to_money(0)
        rows.append({**bucket, "average_ticket": average_ticket})
    return rows


def _sales_by_payment_method(payments: list[Payment]) -> list[dict]:
    totals: dict[str, Decimal] = defaultdict(lambda: to_money(0))
    for payment in payments:
        totals[payment.payment_method] = to_money(totals[payment.payment_method] + payment.total)
    return [
        {"payment_method": method, "total_sales": total}
        for method, total in sorted(totals.items(), key=lambda item: item[0])
    ]


def _services_breakdown(appointments: list[Appointment], payments: list[Payment]) -> tuple[list[dict], list[dict], list[dict]]:
    sold: dict[str, dict] = {}
    for payment in payments:
        appointment = payment.appointment
        if not appointment or not appointment.service:
            continue
        service_name = appointment.service.name
        bucket = sold.setdefault(
            service_name,
            {
                "service_id": appointment.service.id,
                "service_name": service_name,
                "sold_count": 0,
                "revenue": to_money(0),
            },
        )
        bucket["sold_count"] += 1
        bucket["revenue"] = to_money(bucket["revenue"] + payment.total)

    canceled: dict[str, dict] = {}
    duration: dict[str, dict] = {}
    for appointment in appointments:
        if appointment.service:
            service_name = appointment.service.name
        else:
            service_name = f"Servicio {appointment.service_catalog_id}"
        if appointment.status == "cancelado":
            bucket = canceled.setdefault(
                service_name,
                {"service_id": appointment.service_catalog_id, "service_name": service_name, "canceled_count": 0},
            )
            bucket["canceled_count"] += 1
        if appointment.service_job and appointment.service_job.actual_duration_minutes:
            bucket = duration.setdefault(
                service_name,
                {
                    "service_id": appointment.service_catalog_id,
                    "service_name": service_name,
                    "total_minutes": 0,
                    "services_count": 0,
                },
            )
            bucket["total_minutes"] += appointment.service_job.actual_duration_minutes
            bucket["services_count"] += 1

    average_duration = []
    for item in duration.values():
        count = item["services_count"]
        average_duration.append(
            {
                "service_id": item["service_id"],
                "service_name": item["service_name"],
                "average_duration_minutes": round(item["total_minutes"] / count, 2) if count else 0,
                "services_count": count,
            }
        )

    return (
        sorted(sold.values(), key=lambda item: (-item["sold_count"], -item["revenue"], item["service_name"])),
        sorted(canceled.values(), key=lambda item: (-item["canceled_count"], item["service_name"])),
        sorted(average_duration, key=lambda item: (-item["services_count"], item["service_name"])),
    )


def _operators_breakdown(appointments: list[Appointment], commissions: list[Commission]) -> list[dict]:
    grouped: dict[int, dict] = {}
    for appointment in appointments:
        if not appointment.operator_id:
            continue
        operator_name = appointment.operator.name if appointment.operator else f"Operador {appointment.operator_id}"
        bucket = grouped.setdefault(
            appointment.operator_id,
            {
                "operator_id": appointment.operator_id,
                "operator_name": operator_name,
                "assigned_services": 0,
                "finished_services": 0,
                "in_progress_services": 0,
                "pending_services": 0,
                "commissions_total": to_money(0),
            },
        )
        bucket["assigned_services"] += 1
        if appointment.status == "terminado":
            bucket["finished_services"] += 1
        elif appointment.status == "en_proceso":
            bucket["in_progress_services"] += 1
        elif appointment.status == "pendiente":
            bucket["pending_services"] += 1

    for commission in commissions:
        if commission.user_id is None:
            continue
        operator_name = commission.user.name if commission.user else f"Operador {commission.user_id}"
        bucket = grouped.setdefault(
            commission.user_id,
            {
                "operator_id": commission.user_id,
                "operator_name": operator_name,
                "assigned_services": 0,
                "finished_services": 0,
                "in_progress_services": 0,
                "pending_services": 0,
                "commissions_total": to_money(0),
            },
        )
        bucket["commissions_total"] = to_money(bucket["commissions_total"] + commission.total_amount)

    return sorted(
        grouped.values(),
        key=lambda item: (-item["finished_services"], -item["commissions_total"], item["operator_name"]),
    )


def _peak_hours(appointments: list[Appointment]) -> list[dict]:
    grouped: dict[int, int] = defaultdict(int)
    for appointment in appointments:
        grouped[appointment.scheduled_start.hour] += 1
    return [
        {"hour": f"{hour:02d}:00", "appointments_count": count}
        for hour, count in sorted(grouped.items(), key=lambda item: (-item[1], item[0]))
    ]


def _frequent_clients(payments: list[Payment]) -> list[dict]:
    grouped: dict[int, dict] = {}
    for payment in payments:
        appointment = payment.appointment
        client = appointment.client if appointment and appointment.client else payment.client
        if not client:
            continue
        bucket = grouped.setdefault(
            client.id,
            {
                "client_id": client.id,
                "client_name": client.name,
                "visits": 0,
                "total_spent": to_money(0),
            },
        )
        bucket["visits"] += 1
        bucket["total_spent"] = to_money(bucket["total_spent"] + payment.total)
    return sorted(grouped.values(), key=lambda item: (-item["visits"], -item["total_spent"], item["client_name"]))


def sales_report(
    session: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    company_id: int | None = None,
    operator_id: int | None = None,
    service_catalog_id: int | None = None,
    payment_method: str | None = None,
) -> dict:
    start_date, end_date = _normalize_window(date_from=date_from, date_to=date_to, default_days=6)
    appointments = _load_filtered_appointments(
        session,
        date_from=start_date,
        date_to=end_date,
        company_id=company_id,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
    )
    payments = _load_filtered_payments(
        session,
        date_from=start_date,
        date_to=end_date,
        company_id=company_id,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
        payment_method=payment_method,
    )
    total_sales = to_money(sum(payment.total for payment in payments))
    transactions = len(payments)
    average_ticket = to_money(total_sales / transactions) if transactions else to_money(0)
    return {
        "date_from": start_date,
        "date_to": end_date,
        "summary": {
            "total_sales": total_sales,
            "transactions": transactions,
            "average_ticket": average_ticket,
        },
        "sales_by_day": _sales_by_day(payments),
        "sales_by_payment_method": _sales_by_payment_method(payments),
        "peak_hours": _peak_hours(appointments),
        "frequent_clients": _frequent_clients(payments),
    }


def services_report(
    session: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    company_id: int | None = None,
    operator_id: int | None = None,
    service_catalog_id: int | None = None,
    payment_method: str | None = None,
) -> dict:
    start_date, end_date = _normalize_window(date_from=date_from, date_to=date_to, default_days=6)
    appointments = _load_filtered_appointments(
        session,
        date_from=start_date,
        date_to=end_date,
        company_id=company_id,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
    )
    payments = _load_filtered_payments(
        session,
        date_from=start_date,
        date_to=end_date,
        company_id=company_id,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
        payment_method=payment_method,
    )
    top_services, canceled_services, average_duration = _services_breakdown(appointments, payments)
    return {
        "date_from": start_date,
        "date_to": end_date,
        "top_services": top_services,
        "canceled_services": canceled_services,
        "average_duration": average_duration,
    }


def commissions_report(
    session: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    company_id: int | None = None,
    operator_id: int | None = None,
) -> dict:
    start_date, end_date = _normalize_window(date_from=date_from, date_to=date_to, default_days=6)
    commissions = _load_filtered_commissions(
        session,
        date_from=start_date,
        date_to=end_date,
        company_id=company_id,
        operator_id=operator_id,
    )
    grouped: dict[int, dict] = {}
    by_day: dict[date, Decimal] = defaultdict(lambda: to_money(0))
    total_amount = to_money(0)
    for commission in commissions:
        total_amount = to_money(total_amount + commission.total_amount)
        if commission.period_date:
            by_day[commission.period_date] = to_money(by_day[commission.period_date] + commission.total_amount)
        operator_name = commission.user.name if commission.user else f"Operador {commission.user_id}"
        bucket = grouped.setdefault(
            commission.user_id,
            {
                "operator_id": commission.user_id,
                "operator_name": operator_name,
                "commissions_count": 0,
                "base_amount": to_money(0),
                "extra_amount": to_money(0),
                "total_amount": to_money(0),
            },
        )
        bucket["commissions_count"] += 1
        bucket["base_amount"] = to_money(bucket["base_amount"] + commission.base_amount)
        bucket["extra_amount"] = to_money(bucket["extra_amount"] + commission.extra_amount)
        bucket["total_amount"] = to_money(bucket["total_amount"] + commission.total_amount)
    return {
        "date_from": start_date,
        "date_to": end_date,
        "summary": {
            "total_amount": total_amount,
            "commissions_count": len(commissions),
        },
        "by_operator": sorted(grouped.values(), key=lambda item: (-item["total_amount"], item["operator_name"])),
        "by_day": [
            {"date": report_day.isoformat(), "total_amount": amount}
            for report_day, amount in sorted(by_day.items(), key=lambda item: item[0])
        ],
    }


def operators_report(
    session: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    company_id: int | None = None,
    operator_id: int | None = None,
    service_catalog_id: int | None = None,
    payment_method: str | None = None,
) -> dict:
    start_date, end_date = _normalize_window(date_from=date_from, date_to=date_to, default_days=6)
    appointments = _load_filtered_appointments(
        session,
        date_from=start_date,
        date_to=end_date,
        company_id=company_id,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
    )
    commissions = _load_filtered_commissions(
        session,
        date_from=start_date,
        date_to=end_date,
        company_id=company_id,
        operator_id=operator_id,
    )
    data = _operators_breakdown(appointments, commissions)
    top_services_operator = data[0] if data else None
    top_commissions_operator = max(data, key=lambda item: item["commissions_total"]) if data else None
    return {
        "date_from": start_date,
        "date_to": end_date,
        "operators": data,
        "top_operator_by_services": top_services_operator,
        "top_operator_by_commissions": top_commissions_operator,
        "payment_method": payment_method,
    }


def daily_report(
    session: Session,
    *,
    target_date: date | None = None,
    company_id: int | None = None,
    operator_id: int | None = None,
    service_catalog_id: int | None = None,
    payment_method: str | None = None,
) -> dict:
    report_day = target_date or date.today()
    appointments = _load_filtered_appointments(
        session,
        date_from=report_day,
        date_to=report_day,
        company_id=company_id,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
    )
    payments = _load_filtered_payments(
        session,
        date_from=report_day,
        date_to=report_day,
        company_id=company_id,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
        payment_method=payment_method,
    )
    commissions = _load_filtered_commissions(
        session,
        date_from=report_day,
        date_to=report_day,
        company_id=company_id,
        operator_id=operator_id,
    )
    services_data = services_report(
        session,
        date_from=report_day,
        date_to=report_day,
        company_id=company_id,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
        payment_method=payment_method,
    )
    operator_data = _operators_breakdown(appointments, commissions)
    summary = calculate_cash_cut_summary(session, target_date=report_day, company_id=company_id)
    summary["ticket_average"] = to_money(summary["total_sales"] / len(payments)) if payments else to_money(0)
    summary["frequent_clients_count"] = len(_frequent_clients(payments))
    return {
        "target_date": report_day,
        "summary": summary,
        "sales_by_payment_method": _sales_by_payment_method(payments),
        "sales_by_day": _sales_by_day(payments),
        "top_services": services_data["top_services"],
        "canceled_services": services_data["canceled_services"],
        "average_duration": services_data["average_duration"],
        "peak_hours": _peak_hours(appointments),
        "frequent_clients": _frequent_clients(payments),
        "operators": operator_data,
        "top_operator_by_services": operator_data[0] if operator_data else None,
        "top_operator_by_commissions": (
            max(operator_data, key=lambda item: item["commissions_total"]) if operator_data else None
        ),
    }


def weekly_report(
    session: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    company_id: int | None = None,
    operator_id: int | None = None,
    service_catalog_id: int | None = None,
    payment_method: str | None = None,
) -> dict:
    start_date, end_date = _normalize_window(date_from=date_from, date_to=date_to, default_days=6)
    sales = sales_report(
        session,
        date_from=start_date,
        date_to=end_date,
        company_id=company_id,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
        payment_method=payment_method,
    )
    services_data = services_report(
        session,
        date_from=start_date,
        date_to=end_date,
        company_id=company_id,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
        payment_method=payment_method,
    )
    operators_data = operators_report(
        session,
        date_from=start_date,
        date_to=end_date,
        company_id=company_id,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
        payment_method=payment_method,
    )
    commissions_data = commissions_report(
        session,
        date_from=start_date,
        date_to=end_date,
        company_id=company_id,
        operator_id=operator_id,
    )
    return {
        "date_from": start_date,
        "date_to": end_date,
        "sales": sales,
        "services": services_data,
        "operators": operators_data,
        "commissions": commissions_data,
    }


def basic_summary(session: Session, *, target_date: date, company_id: int | None = None) -> dict:
    summary = calculate_cash_cut_summary(session, target_date=target_date, company_id=company_id)
    pending_charges = len(
        [
            appointment
            for appointment in list_pending_charge_appointments(session, company_id=company_id)
            if appointment.scheduled_start.date() <= target_date
            and appointment.status != "cancelado"
        ]
    )
    return {
        **summary,
        "pending_charges": pending_charges,
    }
