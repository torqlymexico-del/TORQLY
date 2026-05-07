from datetime import date

from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.services.exceptions import ServiceError
from app.services.service_jobs import (
    finish_operator_task,
    list_operator_tasks,
    report_operator_issue,
    start_operator_task,
)
from app.services.users import list_assignable_operators


router = APIRouter(prefix="/operator/tasks", tags=["web-operator-tasks"])


@router.get("")
def operator_tasks_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.OPERATOR)),
    target_date: date = Query(default_factory=date.today),
    operator_id: int | None = Query(default=None),
):
    return templates.TemplateResponse(
        request,
        "operator_tasks/index.html",
        base_context(
            request,
            current_user=current_user,
            target_date=target_date,
            operator_id=operator_id,
            operators=list_assignable_operators(db, company_id=current_company_id(current_user)),
            tasks=list_operator_tasks(
                db,
                current_user=current_user,
                target_date=target_date,
                operator_id=operator_id,
            ),
            page_title="Tareas del operador",
        ),
    )


@router.post("/{appointment_id}/start")
def operator_task_start(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.OPERATOR)),
):
    try:
        start_operator_task(db, appointment_id, actor=current_user)
        return redirect_with_message("/operator/tasks", "Servicio iniciado.")
    except ServiceError as exc:
        return redirect_with_message("/operator/tasks", str(exc), "error")


@router.post("/{appointment_id}/finish")
def operator_task_finish(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.OPERATOR)),
):
    try:
        finish_operator_task(db, appointment_id, actor=current_user)
        return redirect_with_message("/operator/tasks", "Servicio terminado.")
    except ServiceError as exc:
        return redirect_with_message("/operator/tasks", str(exc), "error")


@router.post("/{appointment_id}/issue")
def operator_task_issue(
    appointment_id: int,
    note: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.OPERATOR)),
):
    try:
        report_operator_issue(db, appointment_id, actor=current_user, note=note)
        return redirect_with_message("/operator/tasks", "Problema reportado.")
    except ServiceError as exc:
        return redirect_with_message("/operator/tasks", str(exc), "error")
