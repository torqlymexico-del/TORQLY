from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.api.common import raise_api_error
from app.schemas.service_catalog import ServiceCatalogCreate, ServiceCatalogRead, ServiceCatalogUpdate
from app.services.exceptions import ServiceError
from app.services.service_catalog import (
    create_service,
    get_service,
    list_services,
    soft_delete_service,
    update_service,
)


router = APIRouter(prefix="/services-catalog", tags=["services_catalog"])


@router.get("/", response_model=list[ServiceCatalogRead])
def get_services(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    branch: str = Query(default="local"),
) -> list[ServiceCatalogRead]:
    return [
        ServiceCatalogRead.model_validate(service)
        for service in list_services(db, company_id=current_company_id(current_user), branch=branch)
    ]


@router.get("/{service_id}", response_model=ServiceCatalogRead)
def get_service_detail(
    service_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> ServiceCatalogRead:
    try:
        return ServiceCatalogRead.model_validate(get_service(db, service_id, company_id=current_company_id(current_user)))
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/", response_model=ServiceCatalogRead)
def create_service_endpoint(
    payload: ServiceCatalogCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
) -> ServiceCatalogRead:
    try:
        return ServiceCatalogRead.model_validate(create_service(db, payload, actor=current_user))
    except ServiceError as exc:
        raise_api_error(exc)


@router.put("/{service_id}", response_model=ServiceCatalogRead)
def update_service_endpoint(
    service_id: int,
    payload: ServiceCatalogUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
) -> ServiceCatalogRead:
    try:
        return ServiceCatalogRead.model_validate(update_service(db, service_id, payload, actor=current_user))
    except ServiceError as exc:
        raise_api_error(exc)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_service_endpoint(
    service_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
) -> Response:
    try:
        soft_delete_service(db, service_id, actor=current_user)
    except ServiceError as exc:
        raise_api_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
