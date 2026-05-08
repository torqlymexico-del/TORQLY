from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import AppointmentStatus, IntegrationStatus, OrderPaymentStatus, OrderStatus
from app.models import Client, Commission, IntegrationLog, InventoryProduct, Payment, ServiceCatalog, User, Vehicle
from app.models.service_order import ServiceOrder
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

    # ── Orders (ServiceOrder) stats ───────────────────────────────────────────
    _orders_base = (
        select(ServiceOrder)
        .where(ServiceOrder.service_date == target_date)
    )
    if company_id is not None:
        _orders_base = _orders_base.where(ServiceOrder.company_id == company_id)

    today_orders = list(session.scalars(_orders_base.order_by(ServiceOrder.daily_sequence.asc())).all())

    _paid_statuses = [
        OrderPaymentStatus.PAID.value,
        OrderPaymentStatus.PARTIAL.value,
        OrderPaymentStatus.CREDIT.value,
        OrderPaymentStatus.COURTESY.value,
    ]

    orders_revenue_q = select(func.coalesce(func.sum(ServiceOrder.total), 0)).where(
        ServiceOrder.service_date == target_date,
        ServiceOrder.payment_status.in_(_paid_statuses),
        ServiceOrder.status != OrderStatus.CANCELLED.value,
    )
    if company_id is not None:
        orders_revenue_q = orders_revenue_q.where(ServiceOrder.company_id == company_id)
    orders_revenue = session.scalar(orders_revenue_q) or 0

    def _count_status(status: str) -> int:
        return sum(1 for o in today_orders if o.status == status)

    orders_pending_payment = sum(
        1 for o in today_orders
        if o.payment_status == OrderPaymentStatus.PENDING.value and o.status != OrderStatus.CANCELLED.value
    )

    # Per-washer load from today's orders
    washer_load: dict[int, dict] = {}
    for order in today_orders:
        if order.status == OrderStatus.CANCELLED.value:
            continue
        for w in order.washers:
            bucket = washer_load.setdefault(w.user_id, {
                "user_id": w.user_id,
                "name": w.user.name if w.user else f"#{w.user_id}",
                "total": 0,
                "completed": 0,
            })
            bucket["total"] += 1
            if order.status in (OrderStatus.DELIVERED.value, OrderStatus.READY.value):
                bucket["completed"] += 1

    orders_today_summary = [
        {
            "id": o.id,
            "daily_sequence": o.daily_sequence,
            "status": o.status,
            "payment_status": o.payment_status,
            "total": str(o.total),
            "vehicle": {
                "plate": o.vehicle.plates if o.vehicle else None,
                "brand": o.vehicle.brand if o.vehicle else None,
                "model": o.vehicle.model if o.vehicle else None,
                "color": o.vehicle.color if o.vehicle else None,
            } if o.vehicle_id else None,
            "client_name": o.client.name if o.client else None,
            "washer_names": [w.user.name for w in o.washers if w.user],
        }
        for o in today_orders
    ]

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
        "orders": {
            "total_today": len(today_orders),
            "en_cola":    _count_status(OrderStatus.QUEUED.value),
            "en_proceso": _count_status(OrderStatus.IN_PROGRESS.value),
            "listo":      _count_status(OrderStatus.READY.value),
            "entregado":  _count_status(OrderStatus.DELIVERED.value),
            "cancelado":  _count_status(OrderStatus.CANCELLED.value),
            "revenue_today": to_money(orders_revenue),
            "pending_payment": orders_pending_payment,
        },
        "orders_today": orders_today_summary,
        "washer_load": sorted(washer_load.values(), key=lambda x: (-x["total"], x["name"])),
    }
