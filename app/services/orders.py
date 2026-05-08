from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import OrderPaymentStatus, OrderStatus
from app.models import ServiceOrder, ServiceOrderItem, ServiceOrderWasher, User
from app.services.exceptions import NotFoundError, ValidationError


def list_orders(
    session: Session,
    *,
    company_id: int | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
) -> list[ServiceOrder]:
    q = select(ServiceOrder).order_by(ServiceOrder.created_at.desc()).limit(limit)
    if company_id is not None:
        q = q.where(ServiceOrder.company_id == company_id)
    if status:
        q = q.where(ServiceOrder.status == status)
    if date_from:
        q = q.where(ServiceOrder.service_date >= date_from)
    if date_to:
        q = q.where(ServiceOrder.service_date <= date_to)
    return list(session.scalars(q).all())


def get_order(session: Session, order_id: int, *, company_id: int | None = None) -> ServiceOrder:
    order = session.get(ServiceOrder, order_id)
    if not order:
        raise NotFoundError("Orden no encontrada.")
    if company_id is not None and order.company_id != company_id:
        raise NotFoundError("Orden no encontrada.")
    return order


def create_order(
    session: Session,
    *,
    client_id: int | None,
    vehicle_id: int | None,
    items: list[dict],
    is_domicilio: bool = False,
    delivery_address: str | None = None,
    notes: str | None = None,
    cash_session_id: int | None = None,
    actor: User,
    company_id: int | None,
) -> ServiceOrder:
    now = datetime.now(timezone.utc)
    today = now.date()

    # Generate daily sequence
    seq = session.scalar(
        select(func.count(ServiceOrder.id)).where(ServiceOrder.service_date == today)
    ) or 0

    order = ServiceOrder(
        company_id=company_id,
        cash_session_id=cash_session_id,
        client_id=client_id,
        vehicle_id=vehicle_id,
        service_date=today,
        daily_sequence=seq + 1,
        status=OrderStatus.QUEUED.value,
        payment_status=OrderPaymentStatus.PENDING.value,
        is_domicilio=is_domicilio,
        delivery_address=delivery_address,
        notes=notes,
        queued_at=now,
        created_by_id=actor.id,
    )
    session.add(order)
    session.flush()

    subtotal = Decimal(0)
    for item_data in items:
        item = ServiceOrderItem(
            order_id=order.id,
            catalog_id=item_data.get("catalog_id"),
            custom_name=item_data.get("custom_name"),
            description=item_data.get("description"),
            unit_price=Decimal(str(item_data["unit_price"])),
            quantity=int(item_data.get("quantity", 1)),
        )
        session.add(item)
        subtotal += item.unit_price * item.quantity

    order.subtotal = subtotal
    order.total = subtotal

    session.commit()
    session.refresh(order)
    return order


def update_order_status(
    session: Session,
    order_id: int,
    *,
    status: str,
    actor: User,
    company_id: int | None,
    cancellation_reason: str | None = None,
) -> ServiceOrder:
    order = get_order(session, order_id, company_id=company_id)
    now = datetime.now(timezone.utc)

    order.status = status
    if status == OrderStatus.IN_PROGRESS.value and not order.started_at:
        order.started_at = now
    elif status == OrderStatus.READY.value and not order.completed_at:
        order.completed_at = now
    elif status == OrderStatus.DELIVERED.value:
        order.delivered_at = now
    elif status == OrderStatus.CANCELLED.value:
        order.cancelled_at = now
        order.cancelled_by_id = actor.id
        order.cancellation_reason = cancellation_reason

    session.commit()
    session.refresh(order)
    return order


def set_payment(
    session: Session,
    order_id: int,
    *,
    payment_method: str,
    payment_status: str,
    discount_amount: Decimal = Decimal(0),
    discount_reason: str | None = None,
    actor: User,
    company_id: int | None,
) -> ServiceOrder:
    order = get_order(session, order_id, company_id=company_id)
    order.payment_method = payment_method
    order.payment_status = payment_status
    order.discount_amount = discount_amount
    order.discount_reason = discount_reason
    order.total = order.subtotal - discount_amount
    session.commit()
    session.refresh(order)
    return order


def assign_washers(
    session: Session,
    order_id: int,
    *,
    washers: list[dict],
    actor: User,
    company_id: int | None,
) -> ServiceOrder:
    order = get_order(session, order_id, company_id=company_id)

    for w in order.washers:
        session.delete(w)
    session.flush()

    for w_data in washers:
        pct = Decimal(str(w_data.get("commission_percent", 0)))
        commission = (order.total * pct / 100).quantize(Decimal("0.01"))
        washer = ServiceOrderWasher(
            order_id=order.id,
            user_id=int(w_data["user_id"]),
            commission_percent=pct,
            commission_amount=commission,
        )
        session.add(washer)

    session.commit()
    session.refresh(order)
    return order


def add_item(
    session: Session,
    order_id: int,
    *,
    catalog_id: int | None,
    custom_name: str | None,
    unit_price: Decimal,
    quantity: int = 1,
    actor: User,
    company_id: int | None,
) -> ServiceOrder:
    order = get_order(session, order_id, company_id=company_id)
    if order.status == OrderStatus.CANCELLED.value:
        raise ValidationError("No se puede modificar una orden cancelada.")

    item = ServiceOrderItem(
        order_id=order.id,
        catalog_id=catalog_id,
        custom_name=custom_name,
        unit_price=unit_price,
        quantity=quantity,
    )
    session.add(item)
    session.flush()
    _recalculate_order_total(order)
    session.commit()
    session.refresh(order)
    return order


def remove_item(
    session: Session,
    order_id: int,
    item_id: int,
    *,
    actor: User,
    company_id: int | None,
) -> ServiceOrder:
    order = get_order(session, order_id, company_id=company_id)
    item = session.get(ServiceOrderItem, item_id)
    if not item or item.order_id != order_id:
        raise NotFoundError("Item no encontrado.")
    session.delete(item)
    session.flush()
    _recalculate_order_total(order)
    session.commit()
    session.refresh(order)
    return order


def update_order_total(
    session: Session,
    order_id: int,
    *,
    total: Decimal,
    actor: User,
    company_id: int | None,
) -> ServiceOrder:
    order = get_order(session, order_id, company_id=company_id)
    if order.status == OrderStatus.CANCELLED.value:
        raise ValidationError("No se puede modificar una orden cancelada.")
    order.total = total
    session.commit()
    session.refresh(order)
    return order


def _recalculate_order_total(order: ServiceOrder) -> None:
    subtotal = sum(
        (i.unit_price * i.quantity for i in order.items),
        Decimal(0),
    )
    order.subtotal = subtotal
    order.total = subtotal - (order.discount_amount or Decimal(0))
