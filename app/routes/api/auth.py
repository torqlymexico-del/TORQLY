from datetime import timedelta
from typing import Annotated

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.enums import UserRole
from app.models import InviteCode, User
from sqlalchemy import select as sa_select
from app.schemas.auth import LoginRequest, RegisterRequest, Token
from app.schemas.user import UserCreate, UserRead
from app.security import create_access_token, decode_pending_google_token
from app.services.exceptions import ConflictError, ValidationError
from app.services.invite_codes import any_users_exist, validate_and_use_invite_code
from app.services.users import authenticate_user, create_user, create_google_user_from_invite


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


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Annotated[Session, Depends(get_db)]) -> UserRead:
    """Registro público: requiere código de invitación (excepto el primer usuario)."""
    is_first_user = not any_users_exist(db)
    if not is_first_user and not payload.invite_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Se requiere un código de acceso.")

    # Determine role from invite code (or admin if first user)
    role = UserRole.ADMIN
    invite_company_id: int | None = None
    if not is_first_user:
        invite = db.scalar(
            sa_select(InviteCode).where(InviteCode.code == payload.invite_code.upper().strip())
        )
        if not invite or not invite.is_active or invite.used_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código de acceso inválido o ya utilizado.")
        role = UserRole(invite.role)
        invite_company_id = invite.company_id

    create_payload = UserCreate(
        name=payload.name,
        phone=payload.phone,
        password=payload.password,
        email=payload.email,
        role=role,
        company_id=invite_company_id,
        active_company_id=invite_company_id,
    )
    try:
        user = create_user(db, create_payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    # Set branch from invite code and mark it as used
    if not is_first_user:
        try:
            used_invite = validate_and_use_invite_code(db, code=payload.invite_code, user=user)
            user.branch = used_invite.branch
            db.add(user)
            db.commit()
            db.refresh(user)
        except (ValidationError, Exception):
            pass  # user already created, best effort

    token = create_access_token(user.id, expires_delta=timedelta(minutes=settings.access_token_expire_minutes))
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return UserRead.model_validate(user)


class GoogleCompleteRequest(BaseModel):
    invite_code: str


@router.post("/google-complete", response_model=UserRead)
def google_complete(
    payload: GoogleCompleteRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> UserRead:
    """Completa el registro de un usuario nuevo de Google usando un código de invitación."""
    pending_token = request.cookies.get("_google_pending")
    if not pending_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No hay sesión de Google pendiente. Inicia sesión con Google de nuevo.")

    try:
        google_info = decode_pending_google_token(pending_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    try:
        user = create_google_user_from_invite(
            db,
            google_sub=google_info["sub"],
            email=google_info.get("email") or None,
            name=google_info.get("name", ""),
            invite_code=payload.invite_code,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    token = create_access_token(user.id, expires_delta=timedelta(minutes=settings.access_token_expire_minutes))
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.delete_cookie("_google_pending")
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

