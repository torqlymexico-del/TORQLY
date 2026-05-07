import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.routes.web.common import base_context, redirect_with_message, templates
from app.security import create_access_token
from app.services.users import accept_privacy_policy, authenticate_user, get_or_create_google_user


router = APIRouter(tags=["web-auth"])

_OAUTH_STATE_COOKIE = "_oauth_state"
_OAUTH_VERIFIER_COOKIE = "_oauth_cv"


def _set_auth_cookie(response: RedirectResponse, user_id: int) -> None:
    token = create_access_token(user_id, expires_delta=timedelta(minutes=settings.access_token_expire_minutes))
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )


def _needs_policy(user: User) -> bool:
    return user.privacy_policy_version != settings.privacy_policy_version


@router.get("/login")
def login_page(request: Request):
    from app.services.google_oauth import is_configured
    google_login = settings.google_login_enabled and is_configured()
    message = request.query_params.get("message")
    level = request.query_params.get("level", "info")
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        base_context(request, google_login=google_login, message=message, level=level),
    )


@router.post("/login")
def login_submit(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    phone: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
):
    user = authenticate_user(db, phone=phone, password=password)
    if not user:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            base_context(
                request,
                error="Credenciales inválidas o usuario inactivo.",
                google_login=settings.google_login_enabled,
            ),
            status_code=401,
        )
    next_url = "/accept-policy" if _needs_policy(user) else "/"
    response = redirect_with_message(next_url, "Sesión iniciada correctamente.")
    _set_auth_cookie(response, user.id)
    return response


@router.get("/auth/google")
def google_login(request: Request):
    from app.services.google_oauth import get_auth_url, is_configured
    if not is_configured() or not settings.google_login_enabled:
        return redirect_with_message("/login", "Google login no está configurado.")
    auth_url, state, code_verifier = get_auth_url()
    response = RedirectResponse(auth_url, status_code=302)
    response.set_cookie(key=_OAUTH_STATE_COOKIE, value=state, httponly=True, samesite="lax", max_age=600)
    if code_verifier:
        response.set_cookie(key=_OAUTH_VERIFIER_COOKIE, value=code_verifier, httponly=True, samesite="lax", max_age=600)
    return response


@router.get("/auth/google/callback")
def google_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    from app.services.google_oauth import exchange_code
    if error or not code:
        return redirect_with_message("/login", f"Acceso con Google cancelado: {error or 'sin código'}.")

    stored_state = request.cookies.get(_OAUTH_STATE_COOKIE)
    if not stored_state or not secrets.compare_digest(stored_state, state or ""):
        return redirect_with_message("/login", "Error de seguridad en el flujo de Google. Intenta de nuevo.")

    code_verifier = request.cookies.get(_OAUTH_VERIFIER_COOKIE)

    try:
        google_info = exchange_code(code, code_verifier=code_verifier)
    except Exception as exc:
        return redirect_with_message("/login", f"Error al verificar la cuenta de Google: {exc}")

    user = get_or_create_google_user(
        db,
        google_sub=google_info["sub"],
        email=google_info.get("email"),
        name=google_info.get("name", ""),
    )

    next_url = "/accept-policy" if _needs_policy(user) else "/"
    response = redirect_with_message(next_url, f"Bienvenido, {user.name}.")
    _set_auth_cookie(response, user.id)
    response.delete_cookie(_OAUTH_STATE_COOKIE)
    response.delete_cookie(_OAUTH_VERIFIER_COOKIE)
    return response


@router.get("/accept-policy")
def accept_policy_page(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    next: str = "/",
):
    return templates.TemplateResponse(
        request,
        "auth/accept_policy.html",
        base_context(
            request,
            current_user=current_user,
            next_url=next,
            policy_version=settings.privacy_policy_version,
            page_title="Política de privacidad",
        ),
    )


@router.post("/accept-policy")
def accept_policy_submit(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    next_url: Annotated[str, Form(...)] = "/",
):
    accept_privacy_policy(db, current_user, version=settings.privacy_policy_version)
    return redirect_with_message(next_url or "/", "Política de privacidad aceptada.")


@router.post("/logout")
def logout_submit():
    response = redirect_with_message("/login", "Sesión cerrada.")
    response.delete_cookie(settings.auth_cookie_name)
    return response
