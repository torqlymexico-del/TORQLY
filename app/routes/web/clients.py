from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.clients import create_client, get_client, list_clients, soft_delete_client, update_client
from app.services.exceptions import ServiceError


router = APIRouter(prefix="/panel/clientes", tags=["web-clients"])


@router.get("")
def clients_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    edit: int | None = None,
):
    if edit:
        try:
            selected = get_client(db, edit, company_id=current_company_id(current_user))
        except ServiceError as exc:
            return redirect_with_message("/panel/clientes", str(exc), "error")
    else:
        selected = None
    return templates.TemplateResponse(
        request,
        "clients/index.html",
        base_context(
            request,
            current_user=current_user,
            clients=list_clients(db, company_id=current_company_id(current_user)),
            selected=selected,
            page_title="Clientes",
        ),
    )


@router.post("")
def clients_create(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    name: str = Form(...),
    phone: str = Form(...),
    email: str | None = Form(default=None),
    address: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    is_active: bool = Form(default=True),
):
    try:
        create_client(
            db,
            ClientCreate(
                name=name,
                phone=phone,
                email=email or None,
                address=address or None,
                notes=notes or None,
                is_active=is_active,
            ),
            actor=current_user,
        )
        return redirect_with_message("/panel/clientes", "Cliente creado correctamente.")
    except ServiceError as exc:
        return redirect_with_message("/panel/clientes", str(exc), "error")


@router.post("/{client_id}/editar")
def clients_update(
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    name: str = Form(...),
    phone: str = Form(...),
    email: str | None = Form(default=None),
    address: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    is_active: bool = Form(default=True),
):
    try:
        update_client(
            db,
            client_id,
            ClientUpdate(
                name=name,
                phone=phone,
                email=email or None,
                address=address or None,
                notes=notes or None,
                is_active=is_active,
            ),
            actor=current_user,
        )
        return redirect_with_message("/panel/clientes", "Cliente actualizado.")
    except ServiceError as exc:
        return redirect_with_message(f"/panel/clientes?edit={client_id}", str(exc), "error")


@router.post("/{client_id}/eliminar")
def clients_delete(
    client_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    try:
        soft_delete_client(db, client_id, actor=current_user)
        return redirect_with_message("/panel/clientes", "Cliente enviado a baja lógica.")
    except ServiceError as exc:
        return redirect_with_message("/panel/clientes", str(exc), "error")
