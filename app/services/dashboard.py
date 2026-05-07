from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import AppointmentStatus, IntegrationStatus
from app.models import Client, Commission, IntegrationLog, InventoryProduct, Payment, ServiceCatalog, User, Vehicle
from app.services.appointments import agenda_for_day
from app.services.company_scope import created_by_company_clause
from app.services.payments import list_pending_charge_appointments
from app.utils.money import to_money


def _active_count(session: Session, model, *, company_id: int | None = None) -> int:
    query = select(func.count(model.id)).where(created_by_company_clause(model, company_id))
    if hasattr(model, "deleted_at"):
        query = query.where(model.deleted_at.is_(None))
    if hasattr(model, "is_active"):
        query = query.where(model.is_active.is_(True))
    return session.scalar(query) or 0


def dashboard_snapshot(session: Session, *, target_date: date, company_id: int | None = None) -> dict:
    today_appointments = agenda_for_day(session, target_date=target_date, company_id=company_id)
    total_sales_today = (
        session.scalar(
            select(func.coalesce(func.sum(Payment.total), 0))
            .where(created_by_company_clause(Payment, company_id))
            .where(func.date(Payment.paid_at) == target_date)
        )
        or 0
    )
    commissions_today = (
        session.scalar(
            select(func.coalesce(func.sum(Commission.total_amount), 0))
            .join(User, User.id == Commission.user_id, isouter=True)
            .where(User.company_id == company_id if company_id is not None else True)
            .where(Commission.period_date == target_date)
        )
        or 0
    )
    pending_charges_today = len(
        [item for item in list_pending_charge_appointments(session, company_id=company_id) if item.scheduled_start.date() <= target_date]
    )

    status_counts = {
        "pending": len([item for item in today_appointments if item.status == AppointmentStatus.PENDING.value]),
        "in_progress": len([item for item in today_appointments if item.status == AppointmentStatus.IN_PROGRESS.value]),
        "finished": len([item for item in today_appointments if item.status == AppointmentStatus.FINISHED.value]),
    }

    operator_map: dict[int, dict] = {}
    for appointment in today_appointments:
        if not appointment.operator_id:
            continue
        bucket = operator_map.setdefault(
            appointment.operator_id,
            {
                "operator_id": appointment.operator_id,
                "operator_name": appointment.operator.name if appointment.operator else f"Operador {appointment.operator_id}",
                "pending": 0,
                "in_progress": 0,
                "finished": 0,
                "total": 0,
            },
        )
        bucket["total"] += 1
        if appointment.status == AppointmentStatus.PENDING.value:
            bucket["pending"] += 1
        elif appointment.status == AppointmentStatus.IN_PROGRESS.value:
            bucket["in_progress"] += 1
        elif appointment.status == AppointmentStatus.FINISHED.value:
            bucket["finished"] += 1

    low_stock_alerts = list(
        session.scalars(
            select(InventoryProduct)
            .where(created_by_company_clause(InventoryProduct, company_id))
            .where(InventoryProduct.deleted_at.is_(None))
            .where(InventoryProduct.is_active.is_(True))
            .where(InventoryProduct.stock <= InventoryProduct.minimum_stock)
            .order_by(InventoryProduct.stock.asc(), InventoryProduct.name.asc())
            .limit(8)
        ).all()
    )
    recent_integration_errors = list(
        session.scalars(
            select(IntegrationLog)
            .where(IntegrationLog.status == IntegrationStatus.FAILED.value)
            .order_by(IntegrationLog.created_at.desc(), IntegrationLog.id.desc())
            .limit(6)
        ).all()
    )

    return {
        "totals": {
            "users": session.scalar(select(func.count(User.id)).where(User.is_active.is_(True)).where(User.company_id == company_id if company_id is not None else True)) or 0,
            "clients": _active_count(session, Client, company_id=company_id),
            "vehicles": _active_count(session, Vehicle, company_id=company_id),
            "services": _active_count(session, ServiceCatalog, company_id=company_id),
            "appointments_today": len(today_appointments),
            "sales_today": to_money(total_sales_today),
            "commissions_today": to_money(commissions_today),
            "pending_charges_today": pending_charges_today,
            "pending_services_today": status_counts["pending"],
            "in_progress_services_today": status_counts["in_progress"],
            "finished_services_today": status_counts["finished"],
        },
        "appointments_today": today_appointments,
        "operator_load": sorted(operator_map.values(), key=lambda item: (-item["total"], item["operator_name"])),
        "low_stock_alerts": low_stock_alerts,
        "recent_integration_errors": recent_integration_errors,
    }
