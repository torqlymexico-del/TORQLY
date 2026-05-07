from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, get_current_user, require_roles
from app.enums import UserRole
from app.models import CashMovement, CashSession, User
from app.routes.api.common import raise_api_error
from app.services.cash_sessions import (
    add_movement, close_session, get_open_session, list_sessions, open_session, void_movement,
)
from app.services.exceptions import ServiceError


router = APIRouter(prefix="/cash-sessions", tags=["cash-sessions"])


# ── Schemas ─────────────────────────────────────────────────────────────────

class OpenSessionIn(BaseModel):
    opening_amount: Decimal = Decimal(0)
    notes: str | None = None


class CloseSessionIn(BaseModel):
    closing_amount: Decimal
    notes: str | None = None


class MovementIn(BaseModel):
    movement_type: str  # ingreso | egreso | retiro
    category: str = "general"
    amount: Decimal
    description: str | None = None


class VoidMovementIn(BaseModel):
    void_reason: str


class SessionOut(BaseModel):
    id: int
    company_id: int | None
    opened_by_id: int | None
    opening_amount: Decimal
    closed_by_id: int | None = None
    closing_amount: Decimal | None = None
    expected_amount: Decimal | None = None
    difference_amount: Decimal | None = None
    total_sales_cash: Decimal
    total_sales_card: Decimal
    total_sales_transfer: Decimal
    total_sales: Decimal
    total_expenses: Decimal
    status: str
    notes: str | None = None

    model_config = {"from_attributes": True}


class MovementOut(BaseModel):
    id: int
    session_id: int
    movement_type: str
    category: str
    amount: Decimal
    description: str | None = None
    is_void: bool
    void_reason: str | None = None
    created_by_id: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[SessionOut])
def get_sessions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
    limit: int = Query(50, le=200),
):
    return [SessionOut.model_validate(s) for s in list_sessions(db, company_id=current_company_id(current_user), limit=limit)]


@router.get("/open", response_model=SessionOut | None)
def get_open(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    cs = get_open_session(db, company_id=current_company_id(current_user))
    return SessionOut.model_validate(cs) if cs else None


@router.post("/open", response_model=SessionOut)
def open_cash_session(
    payload: OpenSessionIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        cs = open_session(
            db,
            opening_amount=payload.opening_amount,
            notes=payload.notes,
            actor=current_user,
            company_id=current_company_id(current_user),
        )
        return SessionOut.model_validate(cs)
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/{session_id}/close", response_model=SessionOut)
def close_cash_session(
    session_id: int,
    payload: CloseSessionIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        cs = close_session(
            db,
            session_id,
            closing_amount=payload.closing_amount,
            notes=payload.notes,
            actor=current_user,
            company_id=current_company_id(current_user),
        )
        return SessionOut.model_validate(cs)
    except ServiceError as exc:
        raise_api_error(exc)


@router.get("/{session_id}/movements", response_model=list[MovementOut])
def get_session_movements(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    company_id = current_company_id(current_user)
    cs = db.scalar(select(CashSession).where(CashSession.id == session_id, CashSession.company_id == company_id))
    if not cs:
        raise_api_error(ServiceError("Sesión no encontrada."))
    movements = list(db.scalars(
        select(CashMovement)
        .where(CashMovement.session_id == session_id)
        .order_by(CashMovement.id.desc())
    ).all())
    return [MovementOut.model_validate(m) for m in movements]


@router.post("/{session_id}/movements", response_model=MovementOut)
def add_cash_movement(
    session_id: int,
    payload: MovementIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        mv = add_movement(
            db,
            session_id,
            movement_type=payload.movement_type,
            category=payload.category,
            amount=payload.amount,
            description=payload.description,
            actor=current_user,
            company_id=current_company_id(current_user),
        )
        return MovementOut.model_validate(mv)
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/movements/{movement_id}/void", response_model=MovementOut)
def void_cash_movement(
    movement_id: int,
    payload: VoidMovementIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR))],
):
    try:
        mv = void_movement(
            db,
            movement_id,
            void_reason=payload.void_reason,
            actor=current_user,
            company_id=current_company_id(current_user),
        )
        return MovementOut.model_validate(mv)
    except ServiceError as exc:
        raise_api_error(exc)
