from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.api.common import raise_api_error
from app.schemas.cash_cut import CashCutCreate, CashCutRead
from app.services.cash_cuts import create_or_refresh_cash_cut, get_cash_cut_by_date, list_cash_cuts
from app.services.exceptions import ServiceError


router = APIRouter(prefix="/cash-cuts", tags=["cash_cuts"])


def _serialize_cash_cut(cash_cut) -> CashCutRead:
    return CashCutRead(
        id=cash_cut.id,
        cut_date=cash_cut.cut_date,
        cashier_id=cash_cut.cashier_id,
        opened_by_user_id=cash_cut.opened_by_user_id,
        closed_by_user_id=cash_cut.closed_by_user_id,
        opened_at=cash_cut.opened_at,
        closed_at=cash_cut.closed_at,
        total_sales=cash_cut.total_sales,
        cash_total=cash_cut.cash_total,
        card_total=cash_cut.card_total,
        transfer_total=cash_cut.transfer_total,
        courtesy_total=cash_cut.courtesy_total,
        discounts_total=cash_cut.discounts_total,
        commissions_total=cash_cut.commissions_total,
        cost_total=cash_cut.cost_total,
        estimated_profit=cash_cut.estimated_profit,
        services_completed=cash_cut.services_completed,
        services_charged=cash_cut.services_charged,
        services_canceled=cash_cut.services_canceled,
        status=cash_cut.status,
        notes=cash_cut.notes,
        opened_by_name=cash_cut.opened_by.name if cash_cut.opened_by else None,
        closed_by_name=cash_cut.closed_by.name if cash_cut.closed_by else None,
    )


@router.get("/", response_model=list[CashCutRead])
def get_cut_history(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> list[CashCutRead]:
    return [_serialize_cash_cut(item) for item in list_cash_cuts(db, company_id=current_company_id(current_user))]


@router.get("/daily", response_model=CashCutRead | None)
def get_daily_cut(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    target_date: date = Query(...),
) -> CashCutRead | None:
    cash_cut = get_cash_cut_by_date(db, target_date=target_date, company_id=current_company_id(current_user))
    return _serialize_cash_cut(cash_cut) if cash_cut else None


@router.post("/", response_model=CashCutRead)
def create_cash_cut_endpoint(
    payload: CashCutCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> CashCutRead:
    try:
        cash_cut = create_or_refresh_cash_cut(
            db,
            target_date=payload.cut_date,
            actor=current_user,
            close_cut=payload.close_cut,
            notes=payload.notes,
            company_id=current_company_id(current_user),
        )
        return _serialize_cash_cut(cash_cut)
    except ServiceError as exc:
        raise_api_error(exc)
