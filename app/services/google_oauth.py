from __future__ import annotations

from app.config import settings

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def is_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def _default_redirect_uri() -> str:
    return f"{settings.app_public_url}/auth/google/callback"


def _client_config(redirect_uri: str) -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": settings.google_token_uri,
            "redirect_uris": [redirect_uri],
        }
    }


def get_auth_url(redirect_uri: str | None = None) -> tuple[str, str, str | None]:
    """Returns (authorization_url, state, code_verifier) for the OAuth2 redirect.

    code_verifier is non-None when the library uses PKCE (google-auth-oauthlib>=1.2).
    """
    from google_auth_oauthlib.flow import Flow

    uri = redirect_uri or _default_redirect_uri()
    flow = Flow.from_client_config(_client_config(uri), scopes=SCOPES)
    flow.redirect_uri = uri
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
    )
    code_verifier = getattr(flow, "code_verifier", None)
    return auth_url, state, code_verifier


def exchange_code(code: str, redirect_uri: str | None = None, code_verifier: str | None = None) -> dict:
    """Exchange authorization code for Google user info.

    Returns dict with keys: sub, email, name, picture.
    Raises on verification failure.
    """
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token
    from google_auth_oauthlib.flow import Flow

    uri = redirect_uri or _default_redirect_uri()
    flow = Flow.from_client_config(_client_config(uri), scopes=SCOPES)
    flow.redirect_uri = uri
    fetch_kwargs: dict = {"code": code}
    if code_verifier:
        fetch_kwargs["code_verifier"] = code_verifier
    flow.fetch_token(**fetch_kwargs)
    credentials = flow.credentials

    id_info = id_token.verify_oauth2_token(
        credentials.id_token,
        google_requests.Request(),
        settings.google_client_id,
        clock_skew_in_seconds=10,
    )
    return {
        "sub": id_info["sub"],
        "email": id_info.get("email"),
        "name": id_info.get("name", ""),
        "picture": id_info.get("picture"),
    }
