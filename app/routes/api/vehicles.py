from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.api.common import raise_api_error
from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate
from app.services.exceptions import ServiceError
from app.services.vehicles import create_vehicle, get_vehicle, list_vehicles, soft_delete_vehicle, update_vehicle


router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("/", response_model=list[VehicleRead])
def get_vehicles(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> list[VehicleRead]:
    return [
        VehicleRead.model_validate(vehicle)
        for vehicle in list_vehicles(db, company_id=current_company_id(current_user))
    ]


@router.get("/{vehicle_id}", response_model=VehicleRead)
def get_vehicle_detail(
    vehicle_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> VehicleRead:
    try:
        return VehicleRead.model_validate(get_vehicle(db, vehicle_id, company_id=current_company_id(current_user)))
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/", response_model=VehicleRead)
def create_vehicle_endpoint(
    payload: VehicleCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> VehicleRead:
    try:
        return VehicleRead.model_validate(create_vehicle(db, payload, actor=current_user))
    except ServiceError as exc:
        raise_api_error(exc)


@router.put("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle_endpoint(
    vehicle_id: int,
    payload: VehicleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> VehicleRead:
    try:
        return VehicleRead.model_validate(update_vehicle(db, vehicle_id, payload, actor=current_user))
    except ServiceError as exc:
        raise_api_error(exc)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_vehicle_endpoint(
    vehicle_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
) -> Response:
    try:
        soft_delete_vehicle(db, vehicle_id, actor=current_user)
    except ServiceError as exc:
        raise_api_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
