from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, get_current_user, require_roles
from app.enums import UserRole
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.exceptions import ServiceError
from app.services.users import create_user, get_user, list_assignable_operators, list_users, update_user
from app.routes.api.common import raise_api_error


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead])
def get_users(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
) -> list[UserRead]:
    return [UserRead.model_validate(user) for user in list_users(db, company_id=current_company_id(current_user))]


@router.get("/operators", response_model=list[UserRead])
def get_operators(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> list[UserRead]:
    return [
        UserRead.model_validate(user)
        for user in list_assignable_operators(db, company_id=current_company_id(current_user))
    ]


@router.get("/{user_id}", response_model=UserRead)
def get_user_detail(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
) -> UserRead:
    try:
        return UserRead.model_validate(get_user(db, user_id, company_id=current_company_id(current_user)))
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/", response_model=UserRead)
def create_user_endpoint(
    payload: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN)),
) -> UserRead:
    try:
        return UserRead.model_validate(create_user(db, payload, actor=current_user))
    except ServiceError as exc:
        raise_api_error(exc)


@router.put("/{user_id}", response_model=UserRead)
def update_user_endpoint(
    user_id: int,
    payload: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN)),
) -> UserRead:
    try:
        return UserRead.model_validate(update_user(db, user_id, payload, actor=current_user))
    except ServiceError as exc:
        raise_api_error(exc)
