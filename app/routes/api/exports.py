from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.integrations.google.sheets import (
    export_agenda,
    export_commissions,
    export_daily_cut,
    export_daily_sales,
    export_inventory,
)


router = APIRouter(prefix="/exports/google-sheets", tags=["exports"])


@router.post("/daily-cut")
def export_daily_cut_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.CASHIER)),
    target_date: date = Query(default_factory=date.today),
    integration_account_id: int | None = Query(default=None),
):
    return export_daily_cut(
        db,
        target_date=target_date,
        company_id=current_company_id(current_user),
        integration_account_id=integration_account_id,
    )


@router.post("/sales")
def export_sales_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.CASHIER)),
    date_from: date = Query(default_factory=lambda: date.today() - timedelta(days=6)),
    date_to: date = Query(default_factory=date.today),
    integration_account_id: int | None = Query(default=None),
):
    return export_daily_sales(
        db,
        date_from=date_from,
        date_to=date_to,
        company_id=current_company_id(current_user),
        integration_account_id=integration_account_id,
    )


@router.post("/commissions")
def export_commissions_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    date_from: date = Query(default_factory=lambda: date.today() - timedelta(days=6)),
    date_to: date = Query(default_factory=date.today),
    integration_account_id: int | None = Query(default=None),
):
    return export_commissions(
        db,
        date_from=date_from,
        date_to=date_to,
        company_id=current_company_id(current_user),
        integration_account_id=integration_account_id,
    )


@router.post("/inventory")
def export_inventory_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    integration_account_id: int | None = Query(default=None),
):
    return export_inventory(
        db,
        company_id=current_company_id(current_user),
        integration_account_id=integration_account_id,
    )


@router.post("/agenda")
def export_agenda_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.CASHIER)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    target_date: date | None = Query(default=None),
    integration_account_id: int | None = Query(default=None),
):
    return export_agenda(
        db,
        target_date=target_date,
        date_from=date_from,
        date_to=date_to,
        company_id=current_company_id(current_user),
        integration_account_id=integration_account_id,
    )
