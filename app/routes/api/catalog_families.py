from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.enums import UserRole
from app.models import User
from app.routes.api.common import raise_api_error
from app.services.catalog_families import (
    create_family, create_subfamily, list_families, list_subfamilies,
    update_family, update_subfamily,
)
from app.services.exceptions import ServiceError


router = APIRouter(prefix="/catalog", tags=["catalog"])


class FamilyIn(BaseModel):
    name: str
    color_code: str = "#334155"
    sort_order: int = 0
    is_active: bool = True


class SubfamilyIn(BaseModel):
    family_id: int
    name: str
    sort_order: int = 0
    is_active: bool = True


class FamilyOut(BaseModel):
    id: int
    name: str
    color_code: str
    sort_order: int
    is_active: bool
    model_config = {"from_attributes": True}


class SubfamilyOut(BaseModel):
    id: int
    family_id: int
    name: str
    sort_order: int
    is_active: bool
    model_config = {"from_attributes": True}


@router.get("/families", response_model=list[FamilyOut])
def get_families(db: Annotated[Session, Depends(get_db)], current_user=Depends(require_roles())):
    return [FamilyOut.model_validate(f) for f in list_families(db)]


@router.post("/families", response_model=FamilyOut)
def create_family_endpoint(
    payload: FamilyIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    f = create_family(db, name=payload.name, color_code=payload.color_code, sort_order=payload.sort_order)
    return FamilyOut.model_validate(f)


@router.put("/families/{family_id}", response_model=FamilyOut)
def update_family_endpoint(
    family_id: int,
    payload: FamilyIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    try:
        f = update_family(db, family_id, name=payload.name, color_code=payload.color_code, sort_order=payload.sort_order, is_active=payload.is_active)
        return FamilyOut.model_validate(f)
    except ServiceError as exc:
        raise_api_error(exc)


@router.get("/subfamilies", response_model=list[SubfamilyOut])
def get_subfamilies(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles()),
    family_id: int | None = None,
):
    return [SubfamilyOut.model_validate(sf) for sf in list_subfamilies(db, family_id=family_id)]


@router.post("/subfamilies", response_model=SubfamilyOut)
def create_subfamily_endpoint(
    payload: SubfamilyIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    sf = create_subfamily(db, family_id=payload.family_id, name=payload.name, sort_order=payload.sort_order)
    return SubfamilyOut.model_validate(sf)


@router.put("/subfamilies/{subfamily_id}", response_model=SubfamilyOut)
def update_subfamily_endpoint(
    subfamily_id: int,
    payload: SubfamilyIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    try:
        sf = update_subfamily(db, subfamily_id, name=payload.name, sort_order=payload.sort_order, is_active=payload.is_active)
        return SubfamilyOut.model_validate(sf)
    except ServiceError as exc:
        raise_api_error(exc)
