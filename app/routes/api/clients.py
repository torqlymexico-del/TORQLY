from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.api.common import raise_api_error
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.services.clients import create_client, get_client, list_clients, soft_delete_client, update_client
from app.services.exceptions import ServiceError


router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/", response_model=list[ClientRead])
def get_clients(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> list[ClientRead]:
    return [
        ClientRead.model_validate(client)
        for client in list_clients(db, company_id=current_company_id(current_user))
    ]


@router.get("/{client_id}", response_model=ClientRead)
def get_client_detail(
    client_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> ClientRead:
    try:
        return ClientRead.model_validate(get_client(db, client_id, company_id=current_company_id(current_user)))
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/", response_model=ClientRead)
def create_client_endpoint(
    payload: ClientCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> ClientRead:
    try:
        return ClientRead.model_validate(create_client(db, payload, actor=current_user))
    except ServiceError as exc:
        raise_api_error(exc)


@router.put("/{client_id}", response_model=ClientRead)
def update_client_endpoint(
    client_id: int,
    payload: ClientUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> ClientRead:
    try:
        return ClientRead.model_validate(update_client(db, client_id, payload, actor=current_user))
    except ServiceError as exc:
        raise_api_error(exc)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_client_endpoint(
    client_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
) -> Response:
    try:
        soft_delete_client(db, client_id, actor=current_user)
    except ServiceError as exc:
        raise_api_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
