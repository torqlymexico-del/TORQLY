from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.schemas.invite_code import InviteCodeCreate, InviteCodeRead
from app.services.exceptions import ServiceError
from app.services.invite_codes import generate_invite_code, list_invite_codes, revoke_invite_code
from app.routes.api.common import raise_api_error

router = APIRouter(prefix="/invite-codes", tags=["invite-codes"])

ALLOWED_ROLES = {r.value for r in UserRole}


@router.get("/", response_model=list[InviteCodeRead])
def get_invite_codes(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN)),
) -> list[InviteCodeRead]:
    company_id = current_company_id(current_user)
    codes = list_invite_codes(db, company_id=company_id)
    return [
        InviteCodeRead(
            id=c.id,
            code=c.code,
            role=c.role,
            label=c.label,
            is_active=c.is_active,
            created_by_name=c.created_by.name if c.created_by else None,
            used_by_name=c.used_by.name if c.used_by else None,
            used_at=c.used_at,
            created_at=c.created_at,
        )
        for c in codes
    ]


@router.post("/", response_model=InviteCodeRead, status_code=status.HTTP_201_CREATED)
def create_invite_code(
    payload: InviteCodeCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN)),
) -> InviteCodeRead:
    if payload.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=422, detail=f"Rol inválido: {payload.role}")
    company_id = current_company_id(current_user)
    try:
        code = generate_invite_code(
            db,
            company_id=company_id,
            role=payload.role,
            created_by_id=current_user.id,
            label=payload.label,
        )
    except ServiceError as exc:
        raise_api_error(exc)
    return InviteCodeRead(
        id=code.id,
        code=code.code,
        role=code.role,
        label=code.label,
        is_active=code.is_active,
        created_by_name=current_user.name,
        used_by_name=None,
        used_at=None,
        created_at=code.created_at,
    )


@router.delete("/{code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invite_code(
    code_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN)),
) -> None:
    try:
        revoke_invite_code(db, code_id=code_id, company_id=current_company_id(current_user))
    except ServiceError as exc:
        raise_api_error(exc)
