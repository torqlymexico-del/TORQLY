from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, get_current_user
from app.enums import UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.services.exceptions import ServiceError
from app.services.notifications import list_notifications, mark_notification_read
from app.services.users import list_users


router = APIRouter(prefix="/notifications", tags=["web-notifications"])


@router.get("")
def notifications_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    type: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    unread_only: bool = Query(default=False),
):
    selected_user_id = user_id if current_user.role in [UserRole.ADMIN.value, UserRole.SUPERVISOR.value] else None
    return templates.TemplateResponse(
        request,
        "notifications/index.html",
        base_context(
            request,
            current_user=current_user,
            notifications=list_notifications(
                db,
                user=current_user,
                limit=200,
                unread_only=unread_only,
                type=type,
                user_id=selected_user_id,
                date_from=date_from,
                date_to=date_to,
            ),
            users=list_users(db, company_id=current_company_id(current_user)),
            filters={
                "type": type or "",
                "user_id": selected_user_id,
                "date_from": date_from,
                "date_to": date_to,
                "unread_only": unread_only,
            },
            page_title="Notificaciones",
        ),
    )


@router.post("/{notification_id}/read")
def notification_mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        mark_notification_read(db, notification_id, actor=current_user)
        return redirect_with_message("/notifications", "Notificacion marcada como leida.")
    except ServiceError as exc:
        return redirect_with_message("/notifications", str(exc), "error")
