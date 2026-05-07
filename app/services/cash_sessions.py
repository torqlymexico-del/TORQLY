from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import CashMovementType, CashSessionStatus
from app.models import CashMovement, CashSession, User
from app.services.exceptions import ConflictError, NotFoundError, ValidationError


def get_open_session(session: Session, *, company_id: int | None = None) -> CashSession | None:
    q = select(CashSession).where(CashSession.status == CashSessionStatus.OPEN.value)
    if company_id is not None:
        q = q.where(CashSession.company_id == company_id)
    return session.scalar(q)


def list_sessions(session: Session, *, company_id: int | None = None, limit: int = 50) -> list[CashSession]:
    q = (
        select(CashSession)
        .order_by(CashSession.opened_at.desc())
        .limit(limit)
    )
    if company_id is not None:
        q = q.where(CashSession.company_id == company_id)
    return list(session.scalars(q).all())


def open_session(
    session: Session,
    *,
    opening_amount: Decimal,
    notes: str | None,
    actor: User,
    company_id: int | None,
) -> CashSession:
    existing = get_open_session(session, company_id=company_id)
    if existing:
        raise ConflictError("Ya hay una sesión de caja abierta. Ciérrala antes de abrir una nueva.")

    now = datetime.now(timezone.utc)
    cs = CashSession(
        company_id=company_id,
        opened_by_id=actor.id,
        opened_at=now,
        opening_amount=opening_amount,
        status=CashSessionStatus.OPEN.value,
        notes=notes,
    )
    session.add(cs)
    session.commit()
    session.refresh(cs)
    return cs


def close_session(
    session: Session,
    session_id: int,
    *,
    closing_amount: Decimal,
    notes: str | None,
    actor: User,
    company_id: int | None,
) -> CashSession:
    cs = _get_session(session, session_id, company_id=company_id)
    if cs.status != CashSessionStatus.OPEN.value:
        raise ValidationError("La sesión ya está cerrada.")

    now = datetime.now(timezone.utc)
    # Recalculate totals from orders and movements
    _recalculate_totals(session, cs)
    expected = (cs.opening_amount or Decimal(0)) + (cs.total_sales_cash or Decimal(0)) - (cs.total_expenses or Decimal(0))
    cs.expected_amount = expected
    cs.closing_amount = closing_amount
    cs.difference_amount = closing_amount - expected
    cs.closed_by_id = actor.id
    cs.closed_at = now
    cs.status = CashSessionStatus.CLOSED.value
    if notes:
        cs.notes = notes
    session.commit()
    session.refresh(cs)
    return cs


def add_movement(
    session: Session,
    session_id: int,
    *,
    movement_type: str,
    category: str,
    amount: Decimal,
    description: str | None,
    actor: User,
    company_id: int | None,
) -> CashMovement:
    cs = _get_session(session, session_id, company_id=company_id)
    if cs.status != CashSessionStatus.OPEN.value:
        raise ValidationError("No se puede agregar movimientos a una sesión cerrada.")

    mv = CashMovement(
        session_id=cs.id,
        movement_type=movement_type,
        category=category,
        amount=amount,
        description=description,
        created_by_id=actor.id,
    )
    session.add(mv)
    _recalculate_totals(session, cs)
    session.commit()
    session.refresh(mv)
    return mv


def void_movement(
    session: Session,
    movement_id: int,
    *,
    void_reason: str,
    actor: User,
    company_id: int | None,
) -> CashMovement:
    mv = session.get(CashMovement, movement_id)
    if not mv:
        raise NotFoundError("Movimiento no encontrado.")
    cs = _get_session(session, mv.session_id, company_id=company_id)
    if mv.is_void:
        raise ValidationError("El movimiento ya está anulado.")
    if cs.status != CashSessionStatus.OPEN.value:
        raise ValidationError("No se puede anular movimientos de una sesión cerrada.")

    mv.is_void = True
    mv.voided_at = datetime.now(timezone.utc)
    mv.voided_by_id = actor.id
    mv.void_reason = void_reason
    _recalculate_totals(session, cs)
    session.commit()
    session.refresh(mv)
    return mv


def _get_session(session: Session, session_id: int, *, company_id: int | None) -> CashSession:
    cs = session.get(CashSession, session_id)
    if not cs:
        raise NotFoundError("Sesión de caja no encontrada.")
    if company_id is not None and cs.company_id != company_id:
        raise NotFoundError("Sesión de caja no encontrada.")
    return cs


def _recalculate_totals(session: Session, cs: CashSession) -> None:
    movements = [m for m in cs.movements if not m.is_void]
    income = sum(m.amount for m in movements if m.movement_type == CashMovementType.INCOME.value)
    expense = sum(m.amount for m in movements if m.movement_type == CashMovementType.EXPENSE.value)
    withdrawal = sum(m.amount for m in movements if m.movement_type == CashMovementType.WITHDRAWAL.value)

    orders_cash = sum(
        (o.total for o in cs.orders if o.payment_method == "efectivo" and o.payment_status == "pagado"),
        Decimal(0),
    )
    orders_card = sum(
        (o.total for o in cs.orders if o.payment_method == "tarjeta" and o.payment_status == "pagado"),
        Decimal(0),
    )
    orders_transfer = sum(
        (o.total for o in cs.orders if o.payment_method == "transferencia" and o.payment_status == "pagado"),
        Decimal(0),
    )

    cs.total_sales_cash = orders_cash + income
    cs.total_sales_card = orders_card
    cs.total_sales_transfer = orders_transfer
    cs.total_sales = cs.total_sales_cash + cs.total_sales_card + cs.total_sales_transfer
    cs.total_expenses = expense + withdrawal
