import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import IntegrationAccountProvider, IntegrationStatus
from app.services.audit import log_integration_event
from app.services.clickup_webhooks import process_clickup_webhook
from app.services.integration_manager import (
    resolve_whatsapp_account_from_metadata,
    verify_clickup_signature,
    verify_whatsapp_signature,
    verify_whatsapp_token,
)
from app.integrations.whatsapp.webhook import parse_whatsapp_webhook_payload
from app.services.whatsapp_conversations import process_whatsapp_webhook


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _decode_json_body(body: bytes) -> dict:
    if not body:
        return {}
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"JSON invalido: {exc}")


@router.get("/whatsapp")
def whatsapp_verify(request: Request):
    import os as _os
    mode = request.query_params.get("hub.mode", "")
    token = request.query_params.get("hub.verify_token", "").strip().strip('"').strip("'")
    challenge = request.query_params.get("hub.challenge", "")
    if mode != "subscribe" or not token:
        raise HTTPException(status_code=403, detail="Token de verificacion invalido.")
    for env_key in ("META_WHATSAPP_VERIFY_TOKEN", "WHATSAPP_VERIFY_TOKEN"):
        stored = _os.environ.get(env_key, "").strip().strip('"').strip("'")
        if stored and token == stored:
            return PlainTextResponse(challenge or "ok")
    raise HTTPException(status_code=403, detail="Token de verificacion invalido.")


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    body = await request.body()
    payload = _decode_json_body(body)
    inbound_messages, _ = parse_whatsapp_webhook_payload(payload)
    first_metadata = inbound_messages[0].get("metadata") if inbound_messages else {}
    account = resolve_whatsapp_account_from_metadata(db, first_metadata)
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


@router.post("/clickup")
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
