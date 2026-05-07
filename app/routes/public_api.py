from datetime import date, timedelta

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
from app.schemas.bot import BotCommandRequest, BotMessageRead
from app.services.internal_bot import execute_command, list_history
from app.services.reports import (
    commissions_report,
    daily_report,
    operators_report,
    sales_report,
    services_report,
    weekly_report,
)


router = APIRouter(tags=["public-api"])


def _report_filters(
    date_from: date | None,
    date_to: date | None,
    operator_id: int | None,
    service_catalog_id: int | None,
    payment_method: str | None,
) -> dict:
    return {
        "date_from": date_from,
        "date_to": date_to,
        "operator_id": operator_id,
        "service_catalog_id": service_catalog_id,
        "payment_method": payment_method,
    }


@router.post("/bot/command", response_model=BotMessageRead)
def run_bot_command_alias(
    payload: BotCommandRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    result = execute_command(db, command=payload.command, actor=current_user)
    return BotMessageRead(**result)


@router.get("/bot/history", response_model=list[BotMessageRead])
def bot_history_alias(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    limit: int = Query(default=50, ge=1, le=200),
):
    return [BotMessageRead.model_validate(item) for item in list_history(db, user=current_user, limit=limit)]


@router.get("/reports/daily")
def daily_report_alias(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    target_date: date = Query(default_factory=date.today),
    operator_id: int | None = Query(default=None),
    service_catalog_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
):
    return daily_report(
        db,
        target_date=target_date,
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
        payment_method=payment_method,
    )


@router.get("/reports/weekly")
def weekly_report_alias(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    date_from: date = Query(default_factory=lambda: date.today() - timedelta(days=6)),
    date_to: date = Query(default_factory=date.today),
    operator_id: int | None = Query(default=None),
    service_catalog_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
):
    return weekly_report(
        db,
        **_report_filters(date_from, date_to, operator_id, service_catalog_id, payment_method),
    )


@router.get("/reports/operators")
def operators_report_alias(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    operator_id: int | None = Query(default=None),
    service_catalog_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
):
    return operators_report(
        db,
        **_report_filters(date_from, date_to, operator_id, service_catalog_id, payment_method),
    )


@router.get("/reports/services")
def services_report_alias(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    operator_id: int | None = Query(default=None),
    service_catalog_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
):
    return services_report(
        db,
        **_report_filters(date_from, date_to, operator_id, service_catalog_id, payment_method),
    )


@router.get("/reports/sales")
def sales_report_alias(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    operator_id: int | None = Query(default=None),
    service_catalog_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
):
    return sales_report(
        db,
        **_report_filters(date_from, date_to, operator_id, service_catalog_id, payment_method),
    )


@router.get("/reports/commissions")
def commissions_report_alias(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    operator_id: int | None = Query(default=None),
):
    return commissions_report(
        db,
        date_from=date_from,
        date_to=date_to,
        operator_id=operator_id,
    )


@router.post("/exports/google-sheets/daily-cut")
def export_daily_cut_alias(
    db: Session = Depends(get_db),
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


@router.post("/exports/google-sheets/sales")
def export_sales_alias(
    db: Session = Depends(get_db),
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


@router.post("/exports/google-sheets/commissions")
def export_commissions_alias(
    db: Session = Depends(get_db),
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


@router.post("/exports/google-sheets/inventory")
def export_inventory_alias(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    integration_account_id: int | None = Query(default=None),
):
    return export_inventory(
        db,
        company_id=current_company_id(current_user),
        integration_account_id=integration_account_id,
    )


@router.post("/exports/google-sheets/agenda")
def export_agenda_alias(
    db: Session = Depends(get_db),
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
