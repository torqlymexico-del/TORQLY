import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import current_company_id, get_current_user
from app.enums import IntegrationAccountProvider, IntegrationStatus
from app.services.audit import log_integration_event
from app.services.clickup_webhooks import process_clickup_webhook
from app.services.exceptions import NotFoundError, ValidationError
from app.services.integration_manager import (
    account_preview,
    create_integration_account,
    deactivate_integration_account,
    get_by_id,
    list_accounts,
    mark_default,
    resolve_whatsapp_account_from_metadata,
    test_connection,
    update_integration_account,
    verify_clickup_signature,
    verify_whatsapp_signature,
    verify_whatsapp_token,
)
from app.integrations.whatsapp.webhook import parse_whatsapp_webhook_payload
from app.services.whatsapp_conversations import process_whatsapp_webhook


router = APIRouter(prefix="/integrations", tags=["integrations"])


def _decode_json_body(body: bytes) -> dict:
    if not body:
        return {}
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"JSON invalido: {exc}")


def _require_company(current_user) -> int:
    company_id = current_company_id(current_user)
    if not company_id:
        raise HTTPException(status_code=403, detail="Sin empresa activa.")
    return company_id


def _not_found(exc: NotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


def _bad_request(exc: ValidationError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


# ── Accounts CRUD ─────────────────────────────────────────────────────────────

@router.get("/accounts")
def get_accounts(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
    provider: str | None = None,
    include_inactive: bool = True,
) -> list[dict]:
    company_id = _require_company(current_user)
    accounts = list_accounts(db, company_id=company_id, provider=provider, include_inactive=include_inactive)
    return [account_preview(acc) for acc in accounts]


@router.post("/accounts")
def create_account(
    payload: dict,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> dict:
    company_id = _require_company(current_user)
    provider = (payload.get("provider") or "").strip()
    if not provider:
        raise HTTPException(status_code=422, detail="Campo 'provider' requerido.")
    try:
        account = create_integration_account(db, company_id=company_id, provider=provider, data=payload, actor=current_user)
        db.commit()
        return account_preview(account)
    except ValidationError as exc:
        raise _bad_request(exc)


@router.put("/accounts/{integration_id}")
def update_account(
    integration_id: int,
    payload: dict,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> dict:
    company_id = _require_company(current_user)
    try:
        account = update_integration_account(db, company_id=company_id, integration_id=integration_id, data=payload, actor=current_user)
        db.commit()
        return account_preview(account)
    except NotFoundError as exc:
        raise _not_found(exc)
    except ValidationError as exc:
        raise _bad_request(exc)


@router.post("/accounts/{integration_id}/test")
def test_account(
    integration_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> dict:
    company_id = _require_company(current_user)
    try:
        result = test_connection(db, integration_id, company_id=company_id, actor=current_user)
        db.commit()
        return result
    except NotFoundError as exc:
        raise _not_found(exc)
    except Exception as exc:
        db.rollback()
        return {"ok": False, "message": str(exc)}


@router.post("/accounts/{integration_id}/deactivate")
def deactivate_account(
    integration_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> dict:
    company_id = _require_company(current_user)
    try:
        account = deactivate_integration_account(db, company_id=company_id, integration_id=integration_id, actor=current_user)
        db.commit()
        return account_preview(account)
    except NotFoundError as exc:
        raise _not_found(exc)


@router.post("/accounts/{integration_id}/set-default")
def set_default_account(
    integration_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> dict:
    company_id = _require_company(current_user)
    try:
        account = get_by_id(db, company_id, integration_id)
        result = mark_default(db, company_id, account.provider, integration_id, actor=current_user)
        db.commit()
        return account_preview(result)
    except NotFoundError as exc:
        raise _not_found(exc)
    except ValidationError as exc:
        raise _bad_request(exc)


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
def integration_status(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> dict:
    company_id = current_company_id(current_user)
    accounts = list_accounts(db, company_id=company_id, include_inactive=True) if company_id else []
    return {
        "app_public_url": settings.app_public_url,
        "google_calendar_enabled": settings.google_calendar_enabled,
        "google_sheets_enabled": settings.google_sheets_enabled,
        "whatsapp_enabled": settings.whatsapp_enabled,
        "clickup_enabled": settings.clickup_enabled,
        "database_accounts": [
            {
                "id": account.id,
                "provider": account.provider,
                "name": account.name,
                "status": account.status,
                "is_default": account.is_default,
            }
            for account in accounts
        ],
        "warnings": settings.integration_warnings(),
    }


@router.get("/google/callback")
def google_callback_placeholder(current_user=Depends(get_current_user)) -> dict:
    return {"message": "Callback listo para OAuth dinamico. Puedes conectar Google desde el panel admin."}


@router.get("/whatsapp/webhook")
def whatsapp_verify(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    hub_mode: str | None = None,
    hub_challenge: str | None = None,
    hub_verify_token: str | None = None,
):
    token = hub_verify_token or request.query_params.get("hub.verify_token")
    challenge = hub_challenge or request.query_params.get("hub.challenge")
    mode = hub_mode or request.query_params.get("hub.mode")
    if mode == "subscribe" and token and verify_whatsapp_token(db, token):
        return PlainTextResponse(challenge or "ok")
    raise HTTPException(status_code=403, detail="Token de verificacion invalido.")


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    body = await request.body()
    payload = _decode_json_body(body)
    inbound_messages, _ = parse_whatsapp_webhook_payload(payload)
    account = resolve_whatsapp_account_from_metadata(db, inbound_messages[0].get("metadata") if inbound_messages else {})
    if not verify_whatsapp_signature(
        db,
        body=body,
        signature_header=request.headers.get("X-Hub-Signature-256"),
        integration_account=account,
    ):
        raise HTTPException(status_code=403, detail="Firma de webhook invalida.")
    log_integration_event(
        db,
        provider=IntegrationAccountProvider.WHATSAPP_META.value,
        integration_account_id=account.id if account else None,
        event_type="webhook.received",
        status=IntegrationStatus.SUCCESS.value,
        entity_type="webhook",
        entity_id=None,
        request_payload=payload,
    )
    db.commit()
    return {"received": True, **process_whatsapp_webhook(db, payload)}


@router.post("/clickup/webhook")
async def clickup_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    body = await request.body()
    if not verify_clickup_signature(db, body=body, signature_header=request.headers.get("X-Signature")):
        raise HTTPException(status_code=403, detail="Firma ClickUp invalida.")
    payload = _decode_json_body(body)
    result = process_clickup_webhook(db, payload)
    log_integration_event(
        db,
        provider=IntegrationAccountProvider.CLICKUP.value,
        integration_account_id=result.get("integration_account_id"),
        event_type="webhook.received",
        status=IntegrationStatus.SUCCESS.value,
        entity_type="webhook",
        entity_id=None,
        request_payload=payload,
    )
    db.commit()
    return {"received": True, **result}
