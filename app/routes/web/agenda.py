from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, templates
from app.services.appointments import agenda_for_day


router = APIRouter(prefix="/panel/agenda", tags=["web-agenda"])


@router.get("")
def agenda_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    target_date: date = Query(default_factory=date.today),
):
    return templates.TemplateResponse(
        request,
        "agenda/index.html",
        base_context(
            request,
            current_user=current_user,
            appointments=agenda_for_day(db, target_date=target_date, company_id=current_company_id(current_user)),
            target_date=target_date,
            page_title="Agenda",
        ),
    )
