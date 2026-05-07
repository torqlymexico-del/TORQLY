from datetime import date, time

from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.services.clients import list_clients
from app.services.exceptions import ServiceError
from app.services.service_catalog import list_services
from app.services.users import list_assignable_operators
from app.services.whatsapp_conversations import (
    create_appointment_from_conversation,
    get_conversation,
    link_conversation_client,
    list_conversation_messages,
    list_conversations,
    reply_manually,
    set_human_mode,
)


router = APIRouter(prefix="/whatsapp/conversations", tags=["web-whatsapp"])


@router.get("")
def whatsapp_conversations_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    conversation_id: int | None = Query(default=None),
):
    conversations = list_conversations(db)
    selected = None
    if conversation_id:
        try:
            selected = get_conversation(db, conversation_id)
        except ServiceError:
            selected = None
    if selected is None and conversations:
        selected = conversations[0]
    messages = list_conversation_messages(db, selected.id) if selected else []
    payload = selected.payload if selected and selected.payload else {}
    return templates.TemplateResponse(
        request,
        "whatsapp/index.html",
        base_context(
            request,
            current_user=current_user,
            conversations=conversations,
            selected_conversation=selected,
            messages=messages,
            selected_payload=payload,
            clients=list_clients(db),
            services=list_services(db),
            operators=list_assignable_operators(db, company_id=current_company_id(current_user)),
            page_title="WhatsApp",
        ),
    )


@router.post("/{conversation_id}/human-mode")
def whatsapp_toggle_human_mode(
    conversation_id: int,
    enabled: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    try:
        set_human_mode(db, conversation_id, enabled=enabled == "true", actor=current_user)
        action = "activado" if enabled == "true" else "desactivado"
        return redirect_with_message(
            f"/whatsapp/conversations?conversation_id={conversation_id}",
            f"Modo humano {action}.",
        )
    except ServiceError as exc:
        return redirect_with_message(
            f"/whatsapp/conversations?conversation_id={conversation_id}",
            str(exc),
            "error",
        )


@router.post("/{conversation_id}/reply")
def whatsapp_reply(
    conversation_id: int,
    body: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    try:
        result = reply_manually(db, conversation_id, body=body, actor=current_user)
        level = "success" if result.get("delivered") else "error"
        message = (
            "Respuesta enviada correctamente."
            if result.get("delivered")
            else f"Mensaje registrado pero no entregado: {result.get('error')}"
        )
        return redirect_with_message(
            f"/whatsapp/conversations?conversation_id={conversation_id}",
            message,
            level,
        )
    except ServiceError as exc:
        return redirect_with_message(
            f"/whatsapp/conversations?conversation_id={conversation_id}",
            str(exc),
            "error",
        )


@router.post("/{conversation_id}/link-client")
def whatsapp_link_client(
    conversation_id: int,
    client_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    try:
        link_conversation_client(db, conversation_id, client_id=client_id, actor=current_user)
        return redirect_with_message(
            f"/whatsapp/conversations?conversation_id={conversation_id}",
            "Conversacion relacionada al cliente.",
        )
    except ServiceError as exc:
        return redirect_with_message(
            f"/whatsapp/conversations?conversation_id={conversation_id}",
            str(exc),
            "error",
        )


@router.post("/{conversation_id}/create-appointment")
def whatsapp_create_appointment(
    conversation_id: int,
    service_catalog_id: int = Form(...),
    scheduled_date: date = Form(...),
    scheduled_time: time = Form(...),
    operator_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    try:
        parsed_operator_id = int(operator_id) if operator_id and operator_id.strip() else None
        appointment = create_appointment_from_conversation(
            db,
            conversation_id,
            service_catalog_id=service_catalog_id,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            operator_id=parsed_operator_id,
            actor=current_user,
        )
        return redirect_with_message(
            f"/panel/citas?edit={appointment.id}",
            f"Cita {appointment.id} creada desde conversacion.",
        )
    except ServiceError as exc:
        return redirect_with_message(
            f"/whatsapp/conversations?conversation_id={conversation_id}",
            str(exc),
            "error",
        )
