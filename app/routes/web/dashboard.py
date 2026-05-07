from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, get_current_user
from app.enums import UserRole
from app.routes.web.common import base_context, templates
from app.services.dashboard import dashboard_snapshot
from app.services.notifications import list_notifications


router = APIRouter(tags=["web-dashboard"])


@router.get("/")
def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role == UserRole.OPERATOR.value:
        return RedirectResponse("/operator/tasks", status_code=303)
    snapshot = dashboard_snapshot(db, target_date=date.today(), company_id=current_company_id(current_user))
    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        base_context(
            request,
            current_user=current_user,
            snapshot=snapshot,
            recent_notifications=list_notifications(db, user=current_user, limit=6),
            page_title="Dashboard",
        ),
    )
