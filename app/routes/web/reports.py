from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, templates
from app.services.reports import (
    commissions_report,
    daily_report,
    operators_report,
    sales_report,
    services_report,
    weekly_report,
)
from app.services.service_catalog import list_services
from app.services.users import list_assignable_operators


router = APIRouter(prefix="/reports", tags=["web-reports"])


@router.get("")
def reports_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    date_from: date = Query(default_factory=lambda: date.today() - timedelta(days=6)),
    date_to: date = Query(default_factory=date.today),
    operator_id: int | None = Query(default=None),
    service_catalog_id: int | None = Query(default=None),
    payment_method: str | None = Query(default=None),
):
    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "operator_id": operator_id,
        "service_catalog_id": service_catalog_id,
        "payment_method": payment_method,
    }
    return templates.TemplateResponse(
        request,
        "reports/index.html",
        base_context(
            request,
            current_user=current_user,
            filters=filters,
            daily_data=daily_report(
                db,
                target_date=date_to,
                company_id=current_company_id(current_user),
                operator_id=operator_id,
                service_catalog_id=service_catalog_id,
                payment_method=payment_method,
            ),
            weekly_data=weekly_report(
                db,
                date_from=date_from,
                date_to=date_to,
                company_id=current_company_id(current_user),
                operator_id=operator_id,
                service_catalog_id=service_catalog_id,
                payment_method=payment_method,
            ),
            sales_data=sales_report(
                db,
                date_from=date_from,
                date_to=date_to,
                company_id=current_company_id(current_user),
                operator_id=operator_id,
                service_catalog_id=service_catalog_id,
                payment_method=payment_method,
            ),
            services_data=services_report(
                db,
                date_from=date_from,
                date_to=date_to,
                company_id=current_company_id(current_user),
                operator_id=operator_id,
                service_catalog_id=service_catalog_id,
                payment_method=payment_method,
            ),
            operators_data=operators_report(
                db,
                date_from=date_from,
                date_to=date_to,
                company_id=current_company_id(current_user),
                operator_id=operator_id,
                service_catalog_id=service_catalog_id,
                payment_method=payment_method,
            ),
            commissions_data=commissions_report(
                db,
                date_from=date_from,
                date_to=date_to,
                company_id=current_company_id(current_user),
                operator_id=operator_id,
            ),
            operators=list_assignable_operators(db, company_id=current_company_id(current_user)),
            services=list_services(db, company_id=current_company_id(current_user)),
            page_title="Reportes",
        ),
    )
