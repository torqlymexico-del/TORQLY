"""Rutas server-side mínimas requeridas por la SPA React.

Solo maneja el flujo OAuth de Google (que requiere redirección server-side)
y el logout por cookie. Todo lo demás lo gestiona la SPA vía /api/v1/.
"""
from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.config import settings
from app.database import get_db
from app.security import create_access_token

router = APIRouter(tags=["spa-auth"])

_OAUTH_STATE_COOKIE = "_oauth_state"
_OAUTH_VERIFIER_COOKIE = "_oauth_cv"
_OAUTH_REDIRECT_COOKIE = "_oauth_redirect"


def _build_redirect_uri(request: Request) -> str:
    """Build the OAuth callback URI from the actual request host."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/auth/google/callback"


def _set_auth_cookie(response: RedirectResponse, user_id: int) -> None:
    token = create_access_token(
        user_id,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )


@router.get("/auth/google")
def google_login(request: Request):
    from app.services.google_oauth import get_auth_url, is_configured

    if not is_configured() or not settings.google_login_enabled:
        return RedirectResponse("/login?error=Google+login+no+configurado", status_code=302)

    redirect_uri = _build_redirect_uri(request)
    auth_url, state, code_verifier = get_auth_url(redirect_uri)
    response = RedirectResponse(auth_url, status_code=302)
    response.set_cookie(key=_OAUTH_STATE_COOKIE, value=state, httponly=True, samesite="lax", max_age=600)
    response.set_cookie(key=_OAUTH_REDIRECT_COOKIE, value=redirect_uri, httponly=True, samesite="lax", max_age=600)
    if code_verifier:
        response.set_cookie(key=_OAUTH_VERIFIER_COOKIE, value=code_verifier, httponly=True, samesite="lax", max_age=600)
    return response


@router.get("/auth/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    from sqlalchemy.orm import Session
    from app.services.google_oauth import exchange_code
    from app.services.users import get_or_create_google_user

    if error or not code:
        return RedirectResponse(f"/login?error=Google+cancelado%3A+{error or 'sin+codigo'}", status_code=302)

    stored_state = request.cookies.get(_OAUTH_STATE_COOKIE)
    if not stored_state or not secrets.compare_digest(stored_state, state or ""):
        return RedirectResponse("/login?error=Error+de+seguridad.+Intenta+de+nuevo.", status_code=302)

    code_verifier = request.cookies.get(_OAUTH_VERIFIER_COOKIE)
    redirect_uri = request.cookies.get(_OAUTH_REDIRECT_COOKIE) or None

    try:
        google_info = exchange_code(code, redirect_uri=redirect_uri, code_verifier=code_verifier)
    except Exception as exc:
        return RedirectResponse(f"/login?error=Error+Google%3A+{str(exc)[:80]}", status_code=302)

    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        user = get_or_create_google_user(
            db,
            google_sub=google_info["sub"],
            email=google_info.get("email"),
            name=google_info.get("name", ""),
        )
    except Exception as exc:
        return RedirectResponse(f"/login?error=Error+al+crear+usuario%3A+{str(exc)[:80]}", status_code=302)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    response = RedirectResponse("/", status_code=302)
    _set_auth_cookie(response, user.id)
    response.delete_cookie(_OAUTH_STATE_COOKIE)
    response.delete_cookie(_OAUTH_VERIFIER_COOKIE)
    response.delete_cookie(_OAUTH_REDIRECT_COOKIE)
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(settings.auth_cookie_name)
    return response
