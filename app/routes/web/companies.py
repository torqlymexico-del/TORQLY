from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.services.companies import create_company, list_companies
from app.services.exceptions import ServiceError


router = APIRouter(prefix="/settings/companies", tags=["web-companies"])


@router.get("")
def companies_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    return templates.TemplateResponse(
        request,
        "companies/index.html",
        base_context(
            request,
            current_user=current_user,
            companies=list_companies(db),
            page_title="Empresas",
        ),
    )


@router.post("")
def companies_create(
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    try:
        create_company(db, name=name, actor=current_user)
        return redirect_with_message("/settings/companies", "Empresa creada correctamente.")
    except ServiceError as exc:
        return redirect_with_message("/settings/companies", str(exc), "error")
