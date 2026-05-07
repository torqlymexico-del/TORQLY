from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, object_session

from app.config import settings
from app.enums import (
    IntegrationAccountProvider,
    IntegrationAccountStatus,
    IntegrationProvider,
    IntegrationStatus,
)
from app.models import Company, IntegrationAccount, IntegrationLog, User
from app.services.audit import log_action, log_integration_event
from app.services.credential_vault import (
    credential_suffix,
    decrypt_credentials,
    encrypt_credentials,
    mask_sensitive_payload,
)
from app.services.exceptions import NotFoundError, ValidationError


GRAPH_API_URL = "https://graph.facebook.com"
CLICKUP_API_BASE = "https://api.clickup.com/api/v2"


def get_user_company_id(user: User | None) -> int | None:
    if not user:
        return None
    return user.active_company_id or user.company_id


def default_company(session: Session) -> Company | None:
    return session.scalar(select(Company).order_by(Company.id.asc()))


def list_accounts(
    session: Session,
    *,
    company_id: int,
    provider: str | None = None,
    include_inactive: bool = True,
) -> list[IntegrationAccount]:
    query = (
        select(IntegrationAccount)
        .where(IntegrationAccount.company_id == company_id)
        .order_by(
            IntegrationAccount.provider.asc(),
            IntegrationAccount.is_default.desc(),
            IntegrationAccount.name.asc(),
        )
    )
    if provider:
        query = query.where(IntegrationAccount.provider == provider)
    if not include_inactive:
        query = query.where(IntegrationAccount.status == IntegrationAccountStatus.ACTIVE.value)
    return list(session.scalars(query).all())


def get_by_id(session: Session, company_id: int, integration_id: int) -> IntegrationAccount:
    account = session.scalar(
        select(IntegrationAccount)
        .where(IntegrationAccount.id == integration_id)
        .where(IntegrationAccount.company_id == company_id)
    )
    if not account:
        raise NotFoundError("Integracion no encontrada.")
    return account


def get_default(session: Session, company_id: int, provider: str) -> IntegrationAccount | None:
    return session.scalar(
        select(IntegrationAccount)
        .where(IntegrationAccount.company_id == company_id)
        .where(IntegrationAccount.provider == provider)
        .where(IntegrationAccount.is_default.is_(True))
        .where(IntegrationAccount.status == IntegrationAccountStatus.ACTIVE.value)
        .order_by(IntegrationAccount.id.asc())
    )


def get_credentials(account: IntegrationAccount | None) -> dict:
    if not account:
        return {}
    return decrypt_credentials(account.credentials_encrypted)


def log_usage(session: Session, integration_id: int | None) -> None:
    if not integration_id:
        return
    account = session.get(IntegrationAccount, integration_id)
    if not account:
        return
    account.last_used_at = datetime.now(timezone.utc)
    session.flush()


def handle_expired_credentials(
    session: Session,
    integration_id: int | None,
    *,
    error_message: str | None = None,
) -> None:
    if not integration_id:
        return
    account = session.get(IntegrationAccount, integration_id)
    if not account:
        return
    account.status = IntegrationAccountStatus.EXPIRED.value
    session.flush()
    log_integration_event(
        session,
        provider=account.provider,
        integration_account_id=account.id,
        event_type="credentials.expired",
        status=IntegrationStatus.FAILED.value,
        entity_type="integration_account",
        entity_id=account.id,
        error_message=error_message or "Credenciales vencidas o rechazadas por el proveedor.",
    )


def mark_default(
    session: Session,
    company_id: int,
    provider: str,
    integration_id: int,
    *,
    actor: User | None,
) -> IntegrationAccount:
    account = get_by_id(session, company_id, integration_id)
    if account.provider != provider:
        raise ValidationError("La integracion seleccionada no coincide con el proveedor.")

    for item in list_accounts(session, company_id=company_id, provider=provider):
        item.is_default = item.id == account.id

    account.is_default = True
    account.status = account.status or IntegrationAccountStatus.ACTIVE.value
    session.flush()
    log_action(
        session,
        actor=actor,
        action="integrations.mark_default",
        entity_type="integration_account",
        entity_id=account.id,
        description=f"Integracion {account.name} marcada como default.",
        payload={"provider": provider},
    )
    return account


def _provider_credentials_and_config(provider: str, data: dict, existing: IntegrationAccount | None = None) -> tuple[dict, dict]:
    existing_credentials = get_credentials(existing) if existing else {}
    existing_config = dict(existing.config_json or {}) if existing else {}

    def keep_or_new(key: str) -> str | None:
        value = data.get(key)
        if value is None or str(value).strip() == "":
            return existing_credentials.get(key)
        return str(value).strip()

    if provider == IntegrationAccountProvider.WHATSAPP_META.value:
        credentials = {
            "access_token": keep_or_new("access_token"),
            "verify_token": keep_or_new("verify_token"),
            "webhook_secret": keep_or_new("webhook_secret"),
        }
        config = {
            **existing_config,
            "phone_number_id": (data.get("phone_number_id") or existing_config.get("phone_number_id") or "").strip() or None,
            "business_account_id": (data.get("business_account_id") or existing_config.get("business_account_id") or "").strip() or None,
            "api_version": (data.get("api_version") or existing_config.get("api_version") or settings.meta_whatsapp_api_version).strip(),
        }
        return credentials, config

    if provider in {
        IntegrationAccountProvider.GOOGLE_CALENDAR.value,
        IntegrationAccountProvider.GOOGLE_SHEETS.value,
    }:
        auth_type = (data.get("auth_type") or existing_config.get("auth_type") or "service_account").strip()
        credentials = {
            "credentials_json": keep_or_new("credentials_json"),
            "client_id": keep_or_new("client_id"),
            "client_secret": keep_or_new("client_secret"),
            "refresh_token": keep_or_new("refresh_token"),
        }
        config = {
            **existing_config,
            "auth_type": auth_type,
            "calendar_id": (data.get("calendar_id") or existing_config.get("calendar_id") or "primary").strip() or "primary",
            "spreadsheet_id": (data.get("spreadsheet_id") or existing_config.get("spreadsheet_id") or "").strip() or None,
            "token_uri": (data.get("token_uri") or existing_config.get("token_uri") or settings.google_token_uri).strip(),
        }
        return credentials, config

    if provider == IntegrationAccountProvider.CLICKUP.value:
        credentials = {
            "api_token": keep_or_new("api_token"),
            "webhook_secret": keep_or_new("webhook_secret"),
        }
        config = {
            **existing_config,
            "team_id": (data.get("team_id") or existing_config.get("team_id") or "").strip() or None,
            "space_id": (data.get("space_id") or existing_config.get("space_id") or "").strip() or None,
            "folder_id": (data.get("folder_id") or existing_config.get("folder_id") or "").strip() or None,
            "list_id": (data.get("list_id") or existing_config.get("list_id") or "").strip() or None,
        }
        return credentials, config

    if provider == IntegrationAccountProvider.META_BUSINESS.value:
        credentials = {
            "access_token": keep_or_new("access_token"),
        }
        config = {
            **existing_config,
            "business_id": (data.get("business_id") or existing_config.get("business_id") or "").strip() or None,
            "app_id": (data.get("app_id") or existing_config.get("app_id") or "").strip() or None,
            "ad_account_id": (data.get("ad_account_id") or existing_config.get("ad_account_id") or "").strip() or None,
            "page_id": (data.get("page_id") or existing_config.get("page_id") or "").strip() or None,
            "instagram_business_id": (
                data.get("instagram_business_id") or existing_config.get("instagram_business_id") or ""
            ).strip()
            or None,
            "api_version": (data.get("api_version") or existing_config.get("api_version") or settings.meta_whatsapp_api_version).strip(),
        }
        return credentials, config

    credentials = {"secret_value": keep_or_new("secret_value")}
    config = {
        **existing_config,
        "custom_endpoint": (data.get("custom_endpoint") or existing_config.get("custom_endpoint") or "").strip() or None,
    }
    return credentials, config


def _validate_provider_payload(provider: str, credentials: dict, config: dict) -> None:
    if provider == IntegrationAccountProvider.WHATSAPP_META.value:
        if not credentials.get("access_token") or not config.get("phone_number_id"):
            raise ValidationError("WhatsApp requiere access token y phone_number_id.")
    elif provider == IntegrationAccountProvider.GOOGLE_CALENDAR.value:
        if not credentials.get("credentials_json") and not (
            credentials.get("client_id") and credentials.get("client_secret") and credentials.get("refresh_token")
        ):
            raise ValidationError("Google Calendar requiere credentials_json o flujo OAuth completo.")
    elif provider == IntegrationAccountProvider.GOOGLE_SHEETS.value:
        if not config.get("spreadsheet_id"):
            raise ValidationError("Google Sheets requiere spreadsheet_id.")
        if not credentials.get("credentials_json") and not (
            credentials.get("client_id") and credentials.get("client_secret") and credentials.get("refresh_token")
        ):
            raise ValidationError("Google Sheets requiere credentials_json o flujo OAuth completo.")
    elif provider == IntegrationAccountProvider.CLICKUP.value:
        if not credentials.get("api_token") or not config.get("list_id"):
            raise ValidationError("ClickUp requiere api_token y list_id.")
    elif provider == IntegrationAccountProvider.META_BUSINESS.value:
        if not credentials.get("access_token") or not config.get("business_id"):
            raise ValidationError("Meta Business requiere access_token y business_id.")


def create_integration_account(
    session: Session,
    *,
    company_id: int,
    provider: str,
    data: dict,
    actor: User | None,
) -> IntegrationAccount:
    credentials, config = _provider_credentials_and_config(provider, data)
    _validate_provider_payload(provider, credentials, config)
    account = IntegrationAccount(
        company_id=company_id,
        provider=provider,
        name=(data.get("name") or "").strip(),
        description=(data.get("description") or "").strip() or None,
        status=(data.get("status") or IntegrationAccountStatus.ACTIVE.value).strip(),
        is_default=bool(data.get("is_default")),
        credentials_encrypted=encrypt_credentials(credentials),
        config_json=config,
        created_by=actor.id if actor else None,
        last_connected_at=None,
    )
    if not account.name:
        raise ValidationError("La integracion requiere un nombre.")
    session.add(account)
    session.flush()
    if account.is_default:
        mark_default(session, company_id, provider, account.id, actor=actor)
    log_action(
        session,
        actor=actor,
        action="integrations.create",
        entity_type="integration_account",
        entity_id=account.id,
        description=f"Integracion {account.name} creada.",
        payload={
            "provider": provider,
            "config": mask_sensitive_payload(config),
            "credentials": mask_sensitive_payload(credentials),
        },
    )
    return account


def update_integration_account(
    session: Session,
    *,
    company_id: int,
    integration_id: int,
    data: dict,
    actor: User | None,
) -> IntegrationAccount:
    account = get_by_id(session, company_id, integration_id)
    credentials, config = _provider_credentials_and_config(account.provider, data, existing=account)
    _validate_provider_payload(account.provider, credentials, config)

    account.name = (data.get("name") or account.name or "").strip()
    account.description = (data.get("description") or account.description or "").strip() or None
    account.status = (data.get("status") or account.status or IntegrationAccountStatus.ACTIVE.value).strip()
    account.config_json = config
    account.credentials_encrypted = encrypt_credentials(credentials)
    if "expires_at" in data:
        account.expires_at = data.get("expires_at")
    session.flush()

    if data.get("is_default"):
        mark_default(session, company_id, account.provider, account.id, actor=actor)
    elif data.get("unset_default"):
        account.is_default = False

    log_action(
        session,
        actor=actor,
        action="integrations.update",
        entity_type="integration_account",
        entity_id=account.id,
        description=f"Integracion {account.name} actualizada.",
        payload={
            "provider": account.provider,
            "config": mask_sensitive_payload(config),
            "credentials": mask_sensitive_payload(credentials),
        },
    )
    return account


def deactivate_integration_account(
    session: Session,
    *,
    company_id: int,
    integration_id: int,
    actor: User | None,
) -> IntegrationAccount:
    account = get_by_id(session, company_id, integration_id)
    account.status = IntegrationAccountStatus.INACTIVE.value
    account.is_default = False
    session.flush()
    log_action(
        session,
        actor=actor,
        action="integrations.deactivate",
        entity_type="integration_account",
        entity_id=account.id,
        description=f"Integracion {account.name} desactivada.",
    )
    return account


def _settings_fallback(provider: str) -> dict:
    if provider == IntegrationAccountProvider.WHATSAPP_META.value and settings.whatsapp_enabled:
        return {
            "source": "settings",
            "provider": provider,
            "integration_account": None,
            "credentials": {
                "access_token": settings.meta_whatsapp_access_token,
                "verify_token": settings.meta_whatsapp_verify_token,
                "webhook_secret": settings.meta_whatsapp_webhook_secret,
            },
            "config": {
                "phone_number_id": settings.meta_whatsapp_phone_number_id,
                "business_account_id": settings.meta_whatsapp_business_account_id,
                "api_version": settings.meta_whatsapp_api_version,
            },
        }
    if provider == IntegrationAccountProvider.GOOGLE_CALENDAR.value and settings.google_calendar_enabled:
        return {
            "source": "settings",
            "provider": provider,
            "integration_account": None,
            "credentials": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": settings.google_refresh_token,
            },
            "config": {
                "calendar_id": settings.google_calendar_id,
                "token_uri": settings.google_token_uri,
                "service_account_file": settings.google_service_account_file,
            },
        }
    if provider == IntegrationAccountProvider.GOOGLE_SHEETS.value and settings.google_sheets_enabled:
        return {
            "source": "settings",
            "provider": provider,
            "integration_account": None,
            "credentials": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": settings.google_refresh_token,
            },
            "config": {
                "spreadsheet_id": settings.google_sheets_spreadsheet_id,
                "token_uri": settings.google_token_uri,
                "service_account_file": settings.google_sheets_credentials_file or settings.google_service_account_file,
            },
        }
    if provider == IntegrationAccountProvider.CLICKUP.value and settings.clickup_enabled:
        return {
            "source": "settings",
            "provider": provider,
            "integration_account": None,
            "credentials": {
                "api_token": settings.clickup_api_token,
                "webhook_secret": settings.clickup_webhook_secret,
            },
            "config": {
                "team_id": settings.clickup_team_id,
                "space_id": settings.clickup_space_id,
                "folder_id": settings.clickup_folder_id,
                "list_id": settings.clickup_list_id,
            },
        }
    return {
        "source": "none",
        "provider": provider,
        "integration_account": None,
        "credentials": {},
        "config": {},
    }


def resolve_provider_account(
    session: Session,
    *,
    company_id: int | None,
    provider: str,
    selected_id: int | None = None,
    allow_settings_fallback: bool = True,
) -> dict:
    account = None
    if selected_id and company_id is None:
        account = session.get(IntegrationAccount, selected_id)
    elif company_id and selected_id:
        account = get_by_id(session, company_id, selected_id)
    elif company_id:
        account = get_default(session, company_id, provider)
    elif selected_id is None:
        account = session.scalar(
            select(IntegrationAccount)
            .where(IntegrationAccount.provider == provider)
            .where(IntegrationAccount.is_default.is_(True))
            .where(IntegrationAccount.status == IntegrationAccountStatus.ACTIVE.value)
            .order_by(IntegrationAccount.id.asc())
        )

    if account:
        try:
            credentials = get_credentials(account)
        except Exception as exc:
            return {
                "source": "none",
                "provider": provider,
                "integration_account": account,
                "credentials": {},
                "config": dict(account.config_json or {}),
                "error": str(exc),
            }
        return {
            "source": "database",
            "provider": provider,
            "integration_account": account,
            "credentials": credentials,
            "config": dict(account.config_json or {}),
        }
    if allow_settings_fallback:
        return _settings_fallback(provider)
    return {
        "source": "none",
        "provider": provider,
        "integration_account": None,
        "credentials": {},
        "config": {},
    }


def test_connection(session: Session, integration_id: int, *, company_id: int, actor: User | None = None) -> dict:
    account = get_by_id(session, company_id, integration_id)
    credentials = get_credentials(account)
    config = dict(account.config_json or {})
    result = {"ok": False, "message": "Proveedor no soportado."}

    try:
        if account.provider == IntegrationAccountProvider.WHATSAPP_META.value:
            url = f"{GRAPH_API_URL}/{config.get('api_version') or settings.meta_whatsapp_api_version}/{config.get('phone_number_id')}"
            response = httpx.get(
                url,
                headers={"Authorization": f"Bearer {credentials.get('access_token', '')}"},
                params={"fields": "display_phone_number,verified_name"},
                timeout=20.0,
            )
            response.raise_for_status()
            data = response.json()
            result = {"ok": True, "message": f"WhatsApp conectado: {data.get('display_phone_number') or account.name}"}
        elif account.provider == IntegrationAccountProvider.CLICKUP.value:
            url = f"{CLICKUP_API_BASE}/list/{config.get('list_id')}"
            response = httpx.get(
                url,
                headers={"Authorization": credentials.get("api_token", "")},
                timeout=20.0,
            )
            response.raise_for_status()
            data = response.json()
            result = {"ok": True, "message": f"ClickUp listo: {data.get('name') or config.get('list_id')}"}
        elif account.provider == IntegrationAccountProvider.META_BUSINESS.value:
            version = config.get("api_version") or settings.meta_whatsapp_api_version
            url = f"{GRAPH_API_URL}/{version}/{config.get('business_id')}"
            response = httpx.get(
                url,
                headers={"Authorization": f"Bearer {credentials.get('access_token', '')}"},
                params={"fields": "id,name"},
                timeout=20.0,
            )
            response.raise_for_status()
            data = response.json()
            result = {"ok": True, "message": f"Meta Business listo: {data.get('name') or data.get('id')}"}
        elif account.provider in {
            IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            IntegrationAccountProvider.GOOGLE_SHEETS.value,
        }:
            from app.integrations.google.auth import load_google_credentials_from_runtime

            scopes = (
                settings.google_calendar_scope_list
                if account.provider == IntegrationAccountProvider.GOOGLE_CALENDAR.value
                else settings.google_sheets_scope_list
            )
            google_credentials, error = load_google_credentials_from_runtime(
                credentials=credentials,
                config=config,
                scopes=scopes,
            )
            if error:
                raise ValidationError(error)
            from googleapiclient.discovery import build

            if account.provider == IntegrationAccountProvider.GOOGLE_CALENDAR.value:
                service = build("calendar", "v3", credentials=google_credentials, cache_discovery=False)
                calendar = service.calendars().get(calendarId=config.get("calendar_id") or "primary").execute()
                result = {"ok": True, "message": f"Google Calendar listo: {calendar.get('summary') or calendar.get('id')}"}
            else:
                service = build("sheets", "v4", credentials=google_credentials, cache_discovery=False)
                sheet = service.spreadsheets().get(
                    spreadsheetId=config.get("spreadsheet_id"),
                    includeGridData=False,
                ).execute()
                result = {"ok": True, "message": f"Google Sheets listo: {sheet.get('properties', {}).get('title') or config.get('spreadsheet_id')}"}
    except Exception as exc:  # pragma: no cover - external provider branch
        account.status = IntegrationAccountStatus.ERROR.value
        session.flush()
        result = {"ok": False, "message": str(exc)}

    if result["ok"]:
        account.status = IntegrationAccountStatus.ACTIVE.value
        account.last_connected_at = datetime.now(timezone.utc)
        log_usage(session, account.id)
    log_action(
        session,
        actor=actor,
        action="integrations.test",
        entity_type="integration_account",
        entity_id=account.id,
        description=f"Prueba de conexion para {account.name}.",
        payload={"result": mask_sensitive_payload(result)},
    )
    log_integration_event(
        session,
        provider=account.provider,
        integration_account_id=account.id,
        event_type="connection.test",
        status=IntegrationStatus.SUCCESS.value if result["ok"] else IntegrationStatus.FAILED.value,
        entity_type="integration_account",
        entity_id=account.id,
        response_payload=mask_sensitive_payload(result),
        error_message=None if result["ok"] else result["message"],
    )
    return result


def account_preview(account: IntegrationAccount) -> dict:
    try:
        credentials = get_credentials(account)
        suffix = credential_suffix(
            credentials,
            "access_token",
            "refresh_token",
            "api_token",
            "secret_value",
        )
    except Exception:
        credentials = {}
        suffix = None
    config = dict(account.config_json or {})
    last_error = account_last_error(account)
    return {
        "id": account.id,
        "provider": account.provider,
        "name": account.name,
        "description": account.description,
        "status": account.status,
        "is_default": account.is_default,
        "suffix": suffix,
        "last_connected_at": account.last_connected_at,
        "last_used_at": account.last_used_at,
        "expires_at": account.expires_at,
        "config": mask_sensitive_payload(config),
        "last_error": last_error.error_message if last_error else None,
    }


def account_last_error(account: IntegrationAccount) -> IntegrationLog | None:
    session = object_session(account)
    if session is None:
        return None
    return session.scalar(
        select(IntegrationLog)
        .where(IntegrationLog.integration_account_id == account.id)
        .where(IntegrationLog.status == IntegrationStatus.FAILED.value)
        .order_by(IntegrationLog.created_at.desc(), IntegrationLog.id.desc())
    )


def verify_whatsapp_token(session: Session, token: str) -> bool:
    if settings.meta_whatsapp_verify_token and token == settings.meta_whatsapp_verify_token:
        return True
    accounts = session.scalars(
        select(IntegrationAccount).where(
            IntegrationAccount.provider == IntegrationAccountProvider.WHATSAPP_META.value
        )
    ).all()
    return any(get_credentials(account).get("verify_token") == token for account in accounts)


def resolve_whatsapp_account_from_metadata(session: Session, metadata: dict | None) -> IntegrationAccount | None:
    metadata = metadata or {}
    phone_number_id = str(metadata.get("phone_number_id") or "").strip()
    business_account_id = str(metadata.get("business_account_id") or "").strip()
    if not phone_number_id and not business_account_id:
        return None

    accounts = session.scalars(
        select(IntegrationAccount)
        .where(IntegrationAccount.provider == IntegrationAccountProvider.WHATSAPP_META.value)
        .where(IntegrationAccount.status != IntegrationAccountStatus.INACTIVE.value)
    ).all()
    for account in accounts:
        config = dict(account.config_json or {})
        if phone_number_id and str(config.get("phone_number_id") or "").strip() == phone_number_id:
            return account
        if business_account_id and str(config.get("business_account_id") or "").strip() == business_account_id:
            return account
    return None


def verify_whatsapp_signature(
    session: Session,
    *,
    body: bytes,
    signature_header: str | None,
    integration_account: IntegrationAccount | None = None,
) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return not settings.meta_whatsapp_webhook_secret and integration_account is None
    candidate_secrets: list[str] = []
    if integration_account is not None:
        secret = get_credentials(integration_account).get("webhook_secret")
        if secret:
            candidate_secrets.append(secret)
    if settings.meta_whatsapp_webhook_secret:
        candidate_secrets.append(settings.meta_whatsapp_webhook_secret)
    if not candidate_secrets:
        return True
    received = signature_header.split("=", 1)[1].strip()
    for secret in candidate_secrets:
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, received):
            return True
    return False


def verify_clickup_signature(session: Session, *, body: bytes, signature_header: str | None) -> bool:
    secrets: list[str] = []
    if settings.clickup_webhook_secret:
        secrets.append(settings.clickup_webhook_secret)
    accounts = session.scalars(
        select(IntegrationAccount)
        .where(IntegrationAccount.provider == IntegrationAccountProvider.CLICKUP.value)
        .where(IntegrationAccount.status != IntegrationAccountStatus.INACTIVE.value)
    ).all()
    for account in accounts:
        secret = get_credentials(account).get("webhook_secret")
        if secret:
            secrets.append(secret)
    if not secrets:
        return True
    if not signature_header:
        return False
    return any(
        hmac.compare_digest(
            hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest(),
            signature_header.strip(),
        )
        for secret in secrets
    )
