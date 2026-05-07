from datetime import date

from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.services.cash_cuts import calculate_cash_cut_summary, create_or_refresh_cash_cut, list_cash_cuts
from app.services.exceptions import ServiceError


router = APIRouter(tags=["web-cash-cuts"])


@router.get("/cash-cuts")
def cash_cuts_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    target_date: date = Query(default_factory=date.today),
):
    company_id = current_company_id(current_user)
    summary = calculate_cash_cut_summary(db, target_date=target_date, company_id=company_id)
    return templates.TemplateResponse(
        request,
        "cash_cuts/index.html",
        base_context(
            request,
            current_user=current_user,
            summary=summary,
            target_date=target_date,
            cash_cuts=list_cash_cuts(db, company_id=company_id),
            page_title="Cortes de caja",
        ),
    )


@router.post("/cash-cuts")
def cash_cuts_submit(
    cut_date: date = Form(...),
    close_cut: bool = Form(default=False),
    notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
):
    try:
        create_or_refresh_cash_cut(
            db,
            target_date=cut_date,
            actor=current_user,
            close_cut=close_cut,
            notes=notes,
            company_id=current_company_id(current_user),
        )
        action_label = "cerrado" if close_cut else "actualizado"
        return redirect_with_message(
            f"/cash-cuts?target_date={cut_date.isoformat()}",
            f"Corte {action_label} correctamente.",
        )
    except ServiceError as exc:
        return redirect_with_message(f"/cash-cuts?target_date={cut_date.isoformat()}", str(exc), "error")
