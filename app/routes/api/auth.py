from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserRead
from app.security import create_access_token
from app.services.users import authenticate_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> Token:
    user = authenticate_user(db, phone=payload.phone, password=payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas.")
    token = create_access_token(user.id, expires_delta=timedelta(minutes=720))
    return Token(access_token=token)


@router.post("/session", response_model=UserRead)
def session_login(payload: LoginRequest, response: Response, db: Annotated[Session, Depends(get_db)]) -> UserRead:
    """Login para SPA: autentica y devuelve cookie HttpOnly + datos del usuario."""
    user = authenticate_user(db, phone=payload.phone, password=payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas.")
    token = create_access_token(user.id, expires_delta=timedelta(minutes=settings.access_token_expire_minutes))
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return UserRead.model_validate(user)


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
def session_logout(response: Response) -> None:
    """Logout para SPA: elimina la cookie de sesión."""
    response.delete_cookie(settings.auth_cookie_name)


@router.post("/accept-policy", response_model=UserRead)
def accept_policy(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    """Acepta la política de privacidad actual para la sesión activa."""
    from app.services.users import accept_privacy_policy
    user = accept_privacy_policy(db, current_user, version=settings.privacy_policy_version)
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    return UserRead.model_validate(current_user)

