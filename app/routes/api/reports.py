from datetime import date, timedelta
from io import StringIO
import csv
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.schemas.report import BasicSummaryRead
from app.services.reports import (
    basic_summary,
    commissions_report,
    daily_report,
    operators_report,
    sales_report,
    services_report,
    weekly_report,
)


router = APIRouter(prefix="/reports", tags=["reports"])


def _basic_filters(
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


@router.get("/basic-summary", response_model=BasicSummaryRead)
def get_basic_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    target_date: date = Query(default_factory=date.today),
    format: str = Query(default="json", pattern="^(json|csv)$"),
):
    summary = BasicSummaryRead(
        target_date=target_date,
        **basic_summary(db, target_date=target_date, company_id=current_company_id(current_user)),
    )
    if format == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["metric", "value"])
        for key, value in summary.model_dump().items():
            writer.writerow([key, value])
        return PlainTextResponse(buffer.getvalue(), media_type="text/csv")
    return summary


@router.get("/daily")
def get_daily_report(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    target_date: date = Query(default_factory=date.today),
    operator_id: int | None = Query(default=None),
    service_catalog_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
):
    return daily_report(
        db,
        target_date=target_date,
        company_id=current_company_id(current_user),
        operator_id=operator_id,
        service_catalog_id=service_catalog_id,
        payment_method=payment_method,
    )


@router.get("/weekly")
def get_weekly_report(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    date_from: date = Query(default_factory=lambda: date.today() - timedelta(days=6)),
    date_to: date = Query(default_factory=date.today),
    operator_id: int | None = Query(default=None),
    service_catalog_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
):
    return weekly_report(
        db,
        company_id=current_company_id(current_user),
        **_basic_filters(date_from, date_to, operator_id, service_catalog_id, payment_method),
    )


@router.get("/operators")
def get_operators_report(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    operator_id: int | None = Query(default=None),
    service_catalog_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
):
    return operators_report(
        db,
        company_id=current_company_id(current_user),
        **_basic_filters(date_from, date_to, operator_id, service_catalog_id, payment_method),
    )


@router.get("/services")
def get_services_report(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    operator_id: int | None = Query(default=None),
    service_catalog_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
):
    return services_report(
        db,
        company_id=current_company_id(current_user),
        **_basic_filters(date_from, date_to, operator_id, service_catalog_id, payment_method),
    )


@router.get("/sales")
def get_sales_report(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    operator_id: int | None = Query(default=None),
    service_catalog_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
):
    return sales_report(
        db,
        company_id=current_company_id(current_user),
        **_basic_filters(date_from, date_to, operator_id, service_catalog_id, payment_method),
    )


@router.get("/commissions")
def get_commissions_report(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    operator_id: int | None = Query(default=None),
):
    return commissions_report(
        db,
        company_id=current_company_id(current_user),
        date_from=date_from,
        date_to=date_to,
        operator_id=operator_id,
    )
