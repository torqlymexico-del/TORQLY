from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.services.clients import list_clients
from app.services.exceptions import ServiceError
from app.services.vehicles import create_vehicle, get_vehicle, list_vehicles, soft_delete_vehicle, update_vehicle


router = APIRouter(prefix="/panel/vehiculos", tags=["web-vehicles"])


@router.get("")
def vehicles_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    edit: int | None = None,
):
    if edit:
        try:
            selected = get_vehicle(db, edit, company_id=current_company_id(current_user))
        except ServiceError as exc:
            return redirect_with_message("/panel/vehiculos", str(exc), "error")
    else:
        selected = None
    return templates.TemplateResponse(
        request,
        "vehicles/index.html",
        base_context(
            request,
            current_user=current_user,
            vehicles=list_vehicles(db, company_id=current_company_id(current_user)),
            clients=list_clients(db, company_id=current_company_id(current_user)),
            selected=selected,
            page_title="Vehículos",
        ),
    )


@router.post("")
def vehicles_create(
    client_id: int = Form(...),
    brand: str = Form(...),
    model: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    year: int | None = Form(default=None),
    color: str | None = Form(default=None),
    plates: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    is_active: bool = Form(default=True),
):
    try:
        create_vehicle(
            db,
            VehicleCreate(
                client_id=client_id,
                brand=brand,
                model=model,
                year=year,
                color=color or None,
                plates=plates or None,
                notes=notes or None,
                is_active=is_active,
            ),
            actor=current_user,
        )
        return redirect_with_message("/panel/vehiculos", "Vehículo creado correctamente.")
    except ServiceError as exc:
        return redirect_with_message("/panel/vehiculos", str(exc), "error")


@router.post("/{vehicle_id}/editar")
def vehicles_update(
    vehicle_id: int,
    client_id: int = Form(...),
    brand: str = Form(...),
    model: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    year: int | None = Form(default=None),
    color: str | None = Form(default=None),
    plates: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    is_active: bool = Form(default=True),
):
    try:
        update_vehicle(
            db,
            vehicle_id,
            VehicleUpdate(
                client_id=client_id,
                brand=brand,
                model=model,
                year=year,
                color=color or None,
                plates=plates or None,
                notes=notes or None,
                is_active=is_active,
            ),
            actor=current_user,
        )
        return redirect_with_message("/panel/vehiculos", "Vehículo actualizado.")
    except ServiceError as exc:
        return redirect_with_message(f"/panel/vehiculos?edit={vehicle_id}", str(exc), "error")


@router.post("/{vehicle_id}/eliminar")
def vehicles_delete(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    try:
        soft_delete_vehicle(db, vehicle_id, actor=current_user)
        return redirect_with_message("/panel/vehiculos", "Vehículo enviado a baja lógica.")
    except ServiceError as exc:
        return redirect_with_message("/panel/vehiculos", str(exc), "error")
