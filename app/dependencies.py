from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.enums import UserRole
from app.models import User
from app.security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _get_token(request: Request, bearer_token: Annotated[str | None, Depends(oauth2_scheme)]) -> str:
    token = bearer_token or request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado.",
        )
    return token


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    bearer_token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User:
    token = bearer_token or request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado.")
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")
    return user


def require_roles(*allowed_roles: UserRole | str) -> Callable[[User], User]:
    normalized = {role.value if isinstance(role, UserRole) else role for role in allowed_roles}

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if normalized and current_user.role not in normalized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta acción.",
            )
        return current_user

    return dependency


def current_company_id(current_user: User) -> int | None:
    return current_user.active_company_id or current_user.company_id


def can_select_integrations_manually(current_user: User) -> bool:
    if current_user.role == UserRole.ADMIN.value:
        return True
    if not settings.integrations_allow_manual_selection:
        return False
    if current_user.role != UserRole.SUPERVISOR.value:
        return False
    permissions = current_user.permissions or {}
    return permissions.get("can_select_integrations", True)
