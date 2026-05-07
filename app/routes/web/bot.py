from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.services.internal_bot import execute_command, list_history


router = APIRouter(prefix="/bot", tags=["web-bot"])


@router.get("")
def bot_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    history = list_history(db, user=current_user, limit=50)
    latest_result = history[0] if history else None
    return templates.TemplateResponse(
        request,
        "bot/index.html",
        base_context(
            request,
            current_user=current_user,
            history=history,
            latest_result=latest_result,
            page_title="Bot interno",
        ),
    )


@router.post("")
def bot_execute(
    command: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    execute_command(db, command=command, actor=current_user)
    return redirect_with_message("/bot", "Comando ejecutado.")
