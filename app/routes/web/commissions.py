from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, templates
from app.services.commissions import list_commissions, summarize_commissions_by_operator
from app.services.users import list_assignable_operators


router = APIRouter(tags=["web-commissions"])


@router.get("/commissions")
def commissions_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    operator_id: int | None = Query(default=None),
    period: str = Query(default="daily"),
    reference_date: date = Query(default_factory=date.today),
):
    operators = list_assignable_operators(db, company_id=current_company_id(current_user))
    selected_operator = None
    if operator_id:
        selected_operator = next((operator for operator in operators if operator.id == operator_id), None)
    elif operators:
        selected_operator = operators[0]

    if period == "weekly":
        date_from = reference_date - timedelta(days=reference_date.weekday())
        date_to = date_from + timedelta(days=6)
    else:
        date_from = reference_date
        date_to = reference_date

    summaries = []
    commission_rows = []
    if selected_operator:
        summaries = summarize_commissions_by_operator(
            db,
            company_id=current_company_id(current_user),
            operator_id=selected_operator.id,
            date_from=date_from,
            date_to=date_to,
            period=period,
        )
        commission_rows = list_commissions(
            db,
            company_id=current_company_id(current_user),
            operator_id=selected_operator.id,
            date_from=date_from,
            date_to=date_to,
        )

    return templates.TemplateResponse(
        request,
        "commissions/index.html",
        base_context(
            request,
            current_user=current_user,
            operators=operators,
            selected_operator=selected_operator,
            summaries=summaries,
            commission_rows=commission_rows,
            period=period,
            reference_date=reference_date,
            date_from=date_from,
            date_to=date_to,
            page_title="Comisiones",
        ),
    )
