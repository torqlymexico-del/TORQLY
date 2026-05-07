from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.schemas.user import UserCreate, UserUpdate
from app.services.companies import list_companies
from app.services.exceptions import ServiceError
from app.services.users import create_user, get_user, list_users, update_user


router = APIRouter(prefix="/panel/usuarios", tags=["web-users"])


@router.get("")
def users_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    edit: int | None = None,
):
    if edit:
        try:
            selected = get_user(db, edit, company_id=current_company_id(current_user))
        except ServiceError as exc:
            return redirect_with_message("/panel/usuarios", str(exc), "error")
    else:
        selected = None
    return templates.TemplateResponse(
        request,
        "users/index.html",
        base_context(
            request,
            current_user=current_user,
            users=list_users(db, company_id=current_company_id(current_user)),
            companies=list_companies(db),
            selected=selected,
            page_title="Usuarios",
        ),
    )


@router.post("")
def users_create(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
    name: str = Form(...),
    phone: str = Form(...),
    email: str | None = Form(default=None),
    password: str = Form(...),
    company_id: int | None = Form(default=None),
    role: str = Form(default=UserRole.OPERATOR.value),
    clickup_user_id: str | None = Form(default=None),
    weekly_salary: Decimal = Form(default=Decimal("0")),
    commission_percentage: Decimal = Form(default=Decimal("0")),
    is_active: bool = Form(default=True),
    notes: str | None = Form(default=None),
):
    try:
        create_user(
            db,
            UserCreate(
                name=name,
                phone=phone,
                email=email or None,
                company_id=company_id,
                active_company_id=company_id,
                password=password,
                role=UserRole(role),
                clickup_user_id=clickup_user_id or None,
                weekly_salary=weekly_salary,
                commission_percentage=commission_percentage,
                is_active=is_active,
                notes=notes,
            ),
            actor=current_user,
        )
        return redirect_with_message("/panel/usuarios", "Usuario creado correctamente.")
    except ServiceError as exc:
        return redirect_with_message("/panel/usuarios", str(exc), "error")


@router.post("/{user_id}/editar")
def users_update(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
    name: str = Form(...),
    phone: str = Form(...),
    email: str | None = Form(default=None),
    password: str | None = Form(default=None),
    company_id: int | None = Form(default=None),
    role: str = Form(default=UserRole.OPERATOR.value),
    clickup_user_id: str | None = Form(default=None),
    weekly_salary: Decimal = Form(default=Decimal("0")),
    commission_percentage: Decimal = Form(default=Decimal("0")),
    is_active: bool = Form(default=True),
    notes: str | None = Form(default=None),
):
    try:
        update_user(
            db,
            user_id,
            UserUpdate(
                name=name,
                phone=phone,
                email=email or None,
                company_id=company_id,
                active_company_id=company_id,
                password=password or None,
                role=UserRole(role),
                clickup_user_id=clickup_user_id or None,
                weekly_salary=weekly_salary,
                commission_percentage=commission_percentage,
                is_active=is_active,
                notes=notes,
            ),
            actor=current_user,
        )
        return redirect_with_message("/panel/usuarios", "Usuario actualizado.")
    except ServiceError as exc:
        return redirect_with_message(f"/panel/usuarios?edit={user_id}", str(exc), "error")
