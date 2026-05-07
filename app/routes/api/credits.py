from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.enums import UserRole
from app.models import User
from app.routes.api.common import raise_api_error
from app.services.credits import (
    add_charge, add_payment, get_or_create_account, list_accounts, list_movements, update_credit_limit,
)
from app.services.exceptions import ServiceError


router = APIRouter(prefix="/credits", tags=["credits"])


class AccountIn(BaseModel):
    client_id: int
    credit_limit: Decimal = Decimal(0)
    is_active: bool = True
    notes: str | None = None


class MovementIn(BaseModel):
    amount: Decimal
    description: str | None = None
    order_id: int | None = None


class AccountOut(BaseModel):
    id: int
    client_id: int
    credit_limit: Decimal
    current_balance: Decimal
    is_active: bool
    notes: str | None = None
    model_config = {"from_attributes": True}


class MovementOut(BaseModel):
    id: int
    account_id: int
    client_id: int
    order_id: int | None = None
    movement_type: str
    amount: Decimal
    description: str | None = None
    model_config = {"from_attributes": True}


@router.get("/", response_model=list[AccountOut])
def get_accounts(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    return [AccountOut.model_validate(a) for a in list_accounts(db)]


@router.post("/", response_model=AccountOut)
def create_account(
    payload: AccountIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    try:
        a = get_or_create_account(db, payload.client_id, credit_limit=payload.credit_limit, actor=current_user)
        update_credit_limit(db, payload.client_id, credit_limit=payload.credit_limit, is_active=payload.is_active, notes=payload.notes, actor=current_user)
        return AccountOut.model_validate(a)
    except ServiceError as exc:
        raise_api_error(exc)


@router.put("/{client_id}", response_model=AccountOut)
def update_account(
    client_id: int,
    payload: AccountIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    try:
        a = update_credit_limit(db, client_id, credit_limit=payload.credit_limit, is_active=payload.is_active, notes=payload.notes, actor=current_user)
        return AccountOut.model_validate(a)
    except ServiceError as exc:
        raise_api_error(exc)


@router.get("/{client_id}/movements", response_model=list[MovementOut])
def get_movements(
    client_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    return [MovementOut.model_validate(m) for m in list_movements(db, client_id)]


@router.post("/{client_id}/charge", response_model=MovementOut)
def charge_credit(
    client_id: int,
    payload: MovementIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        mv = add_charge(db, client_id, amount=payload.amount, order_id=payload.order_id, description=payload.description, actor=current_user)
        return MovementOut.model_validate(mv)
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/{client_id}/payment", response_model=MovementOut)
def pay_credit(
    client_id: int,
    payload: MovementIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        mv = add_payment(db, client_id, amount=payload.amount, description=payload.description, actor=current_user)
        return MovementOut.model_validate(mv)
    except ServiceError as exc:
        raise_api_error(exc)
