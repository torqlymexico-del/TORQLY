from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import ServiceType, UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.schemas.service_catalog import ServiceCatalogCreate, ServiceCatalogUpdate
from app.services.exceptions import ServiceError
from app.services.service_catalog import (
    create_service,
    get_service,
    list_services,
    soft_delete_service,
    update_service,
)


router = APIRouter(prefix="/panel/servicios", tags=["web-services"])


@router.get("")
def services_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    edit: int | None = None,
):
    if edit:
        try:
            selected = get_service(db, edit, company_id=current_company_id(current_user))
        except ServiceError as exc:
            return redirect_with_message("/panel/servicios", str(exc), "error")
    else:
        selected = None
    return templates.TemplateResponse(
        request,
        "services/index.html",
        base_context(
            request,
            current_user=current_user,
            services=list_services(db, company_id=current_company_id(current_user)),
            selected=selected,
            page_title="Servicios",
        ),
    )


@router.post("")
def services_create(
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    description: str | None = Form(default=None),
    base_price: Decimal = Form(default=Decimal("0")),
    estimated_duration_minutes: int = Form(default=60),
    service_type: str = Form(default=ServiceType.WASH.value),
    is_active: bool = Form(default=True),
):
    try:
        create_service(
            db,
            ServiceCatalogCreate(
                name=name,
                description=description or None,
                base_price=base_price,
                estimated_duration_minutes=estimated_duration_minutes,
                service_type=ServiceType(service_type),
                is_active=is_active,
            ),
            actor=current_user,
        )
        return redirect_with_message("/panel/servicios", "Servicio creado correctamente.")
    except ServiceError as exc:
        return redirect_with_message("/panel/servicios", str(exc), "error")


@router.post("/{service_id}/editar")
def services_update(
    service_id: int,
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    description: str | None = Form(default=None),
    base_price: Decimal = Form(default=Decimal("0")),
    estimated_duration_minutes: int = Form(default=60),
    service_type: str = Form(default=ServiceType.WASH.value),
    is_active: bool = Form(default=True),
):
    try:
        update_service(
            db,
            service_id,
            ServiceCatalogUpdate(
                name=name,
                description=description or None,
                base_price=base_price,
                estimated_duration_minutes=estimated_duration_minutes,
                service_type=ServiceType(service_type),
                is_active=is_active,
            ),
            actor=current_user,
        )
        return redirect_with_message("/panel/servicios", "Servicio actualizado.")
    except ServiceError as exc:
        return redirect_with_message(f"/panel/servicios?edit={service_id}", str(exc), "error")


@router.post("/{service_id}/eliminar")
def services_delete(
    service_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    try:
        soft_delete_service(db, service_id, actor=current_user)
        return redirect_with_message("/panel/servicios", "Servicio enviado a baja lógica.")
    except ServiceError as exc:
        return redirect_with_message("/panel/servicios", str(exc), "error")
