from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.models import User
from app.routes.api.common import raise_api_error
from app.services.exceptions import ServiceError
from app.services.orders import (
    add_item, assign_washers, create_order, get_order, list_orders,
    remove_item, set_payment, update_order_status, update_order_total,
)


router = APIRouter(prefix="/orders", tags=["orders"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ItemIn(BaseModel):
    catalog_id: int | None = None
    custom_name: str | None = None
    description: str | None = None
    unit_price: Decimal
    quantity: int = 1


class WasherIn(BaseModel):
    user_id: int
    commission_percent: Decimal = Decimal(0)


class CreateOrderIn(BaseModel):
    client_id: int | None = None
    vehicle_id: int | None = None
    items: list[ItemIn] = []
    is_domicilio: bool = False
    delivery_address: str | None = None
    notes: str | None = None
    cash_session_id: int | None = None


class UpdateStatusIn(BaseModel):
    status: str
    cancellation_reason: str | None = None


class SetPaymentIn(BaseModel):
    payment_method: str
    payment_status: str
    discount_amount: Decimal = Decimal(0)
    discount_reason: str | None = None


class AssignWashersIn(BaseModel):
    washers: list[WasherIn]


class UpdateTotalIn(BaseModel):
    total: Decimal
    reason: str | None = None


class WasherOut(BaseModel):
    id: int
    user_id: int
    commission_percent: Decimal
    commission_amount: Decimal
    is_paid: bool

    model_config = {"from_attributes": True}


class ItemOut(BaseModel):
    id: int
    catalog_id: int | None = None
    custom_name: str | None = None
    unit_price: Decimal
    quantity: int

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    company_id: int | None = None
    cash_session_id: int | None = None
    client_id: int | None = None
    vehicle_id: int | None = None
    service_date: date | None = None
    daily_sequence: int | None = None
    subtotal: Decimal
    discount_amount: Decimal
    discount_reason: str | None = None
    total: Decimal
    status: str
    payment_status: str
    payment_method: str | None = None
    is_domicilio: bool
    delivery_address: str | None = None
    notes: str | None = None
    items: list[ItemOut] = []
    washers: list[WasherOut] = []

    model_config = {"from_attributes": True}


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[OrderOut])
def get_orders(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR, UserRole.OPERATOR))],
    status: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    limit: int = Query(100, le=500),
):
    orders = list_orders(
        db,
        company_id=current_company_id(current_user),
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return [OrderOut.model_validate(o) for o in orders]


@router.post("/", response_model=OrderOut)
def create_order_endpoint(
    payload: CreateOrderIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        order = create_order(
            db,
            client_id=payload.client_id,
            vehicle_id=payload.vehicle_id,
            items=[i.model_dump() for i in payload.items],
            is_domicilio=payload.is_domicilio,
            delivery_address=payload.delivery_address,
            notes=payload.notes,
            cash_session_id=payload.cash_session_id,
            actor=current_user,
            company_id=current_company_id(current_user),
        )
        return OrderOut.model_validate(order)
    except ServiceError as exc:
        raise_api_error(exc)


@router.get("/{order_id}", response_model=OrderOut)
def get_order_detail(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR, UserRole.OPERATOR))],
):
    try:
        return OrderOut.model_validate(get_order(db, order_id, company_id=current_company_id(current_user)))
    except ServiceError as exc:
        raise_api_error(exc)


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_status(
    order_id: int,
    payload: UpdateStatusIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR, UserRole.OPERATOR))],
):
    try:
        order = update_order_status(
            db, order_id,
            status=payload.status,
            cancellation_reason=payload.cancellation_reason,
            actor=current_user,
            company_id=current_company_id(current_user),
        )
        return OrderOut.model_validate(order)
    except ServiceError as exc:
        raise_api_error(exc)


@router.patch("/{order_id}/payment", response_model=OrderOut)
def set_order_payment(
    order_id: int,
    payload: SetPaymentIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        order = set_payment(
            db, order_id,
            payment_method=payload.payment_method,
            payment_status=payload.payment_status,
            discount_amount=payload.discount_amount,
            discount_reason=payload.discount_reason,
            actor=current_user,
            company_id=current_company_id(current_user),
        )
        return OrderOut.model_validate(order)
    except ServiceError as exc:
        raise_api_error(exc)


@router.put("/{order_id}/washers", response_model=OrderOut)
def set_washers(
    order_id: int,
    payload: AssignWashersIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        order = assign_washers(
            db, order_id,
            washers=[w.model_dump() for w in payload.washers],
            actor=current_user,
            company_id=current_company_id(current_user),
        )
        return OrderOut.model_validate(order)
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/{order_id}/items", response_model=OrderOut)
def add_order_item(
    order_id: int,
    payload: ItemIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        order = add_item(
            db, order_id,
            catalog_id=payload.catalog_id,
            custom_name=payload.custom_name,
            unit_price=payload.unit_price,
            quantity=payload.quantity,
            actor=current_user,
            company_id=current_company_id(current_user),
        )
        return OrderOut.model_validate(order)
    except ServiceError as exc:
        raise_api_error(exc)


@router.patch("/{order_id}/total", response_model=OrderOut)
def update_total(
    order_id: int,
    payload: UpdateTotalIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        order = update_order_total(
            db, order_id,
            total=payload.total,
            actor=current_user,
            company_id=current_company_id(current_user),
        )
        return OrderOut.model_validate(order)
    except ServiceError as exc:
        raise_api_error(exc)


@router.delete("/{order_id}/items/{item_id}", response_model=OrderOut)
def remove_order_item(
    order_id: int,
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        order = remove_item(
            db, order_id, item_id,
            actor=current_user,
            company_id=current_company_id(current_user),
        )
        return OrderOut.model_validate(order)
    except ServiceError as exc:
        raise_api_error(exc)
