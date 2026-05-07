import json
from pathlib import Path

from app.config import settings


def _credentials_modules():
    try:
        from google.oauth2 import credentials as oauth_credentials
        from google.oauth2 import service_account
    except ImportError:
        return None, None, "Las dependencias de Google no estan instaladas."
    return oauth_credentials, service_account, None


def _load_credentials(
    *,
    service_account_file: str | None,
    service_account_info: dict | None = None,
    oauth_payload: dict | None = None,
    token_uri: str | None = None,
    scopes: list[str],
):
    oauth_credentials, service_account, import_error = _credentials_modules()
    if import_error:
        return None, import_error

    if service_account_info:
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes,
        )
        return credentials, None

    if service_account_file:
        service_account_path = Path(service_account_file)
        if service_account_path.exists():
            credentials = service_account.Credentials.from_service_account_file(
                str(service_account_path),
                scopes=scopes,
            )
            return credentials, None
        return None, f"No se encontro el archivo de credenciales configurado: {service_account_file}."

    oauth_data = oauth_payload or {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "refresh_token": settings.google_refresh_token,
    }
    if oauth_data.get("client_id") and oauth_data.get("client_secret") and oauth_data.get("refresh_token"):
        credentials = oauth_credentials.Credentials(
            token=None,
            refresh_token=oauth_data.get("refresh_token"),
            token_uri=token_uri or settings.google_token_uri,
            client_id=oauth_data.get("client_id"),
            client_secret=oauth_data.get("client_secret"),
            scopes=scopes,
        )
        return credentials, None

    return None, "Credenciales insuficientes para Google."


def load_google_credentials():
    return _load_credentials(
        service_account_file=settings.google_service_account_file,
        scopes=settings.google_calendar_scope_list,
    )


def load_google_sheets_credentials():
    service_account_file = settings.google_sheets_credentials_file or settings.google_service_account_file
    return _load_credentials(
        service_account_file=service_account_file,
        scopes=settings.google_sheets_scope_list,
    )


def load_google_credentials_from_runtime(*, credentials: dict, config: dict, scopes: list[str]):
    raw_credentials_json = credentials.get("credentials_json")
    parsed_credentials_json = None
    if raw_credentials_json:
        try:
            parsed_credentials_json = json.loads(raw_credentials_json)
        except json.JSONDecodeError:
            return None, "El credentials_json de Google no es valido."

    service_account_file = config.get("service_account_file")
    if not service_account_file and config.get("credentials_file"):
        service_account_file = config.get("credentials_file")

    oauth_payload = {
        "client_id": credentials.get("client_id"),
        "client_secret": credentials.get("client_secret"),
        "refresh_token": credentials.get("refresh_token"),
    }
    return _load_credentials(
        service_account_file=service_account_file,
        service_account_info=parsed_credentials_json,
        oauth_payload=oauth_payload,
        token_uri=config.get("token_uri") or settings.google_token_uri,
        scopes=scopes,
    )
