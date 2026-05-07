from __future__ import annotations

from datetime import datetime

import httpx

from app.enums import IntegrationAccountProvider, IntegrationStatus
from app.services.audit import log_integration_event
from app.services.integration_manager import (
    handle_expired_credentials,
    log_usage,
    resolve_provider_account,
)
from app.utils.dates import get_timezone


GRAPH_API_URL = "https://graph.facebook.com"


def _log_and_notify_failure(session, exc, account, event_type, entity_type, entity_id, payload, recipient):
    log_integration_event(
        session,
        provider=IntegrationAccountProvider.WHATSAPP_META.value,
        integration_account_id=account.id if account else None,
        event_type=event_type,
        status=IntegrationStatus.FAILED.value,
        entity_type=entity_type,
        entity_id=entity_id,
        request_payload=payload,
        error_message=str(exc),
    )
    try:
        from app.services.notifications import notify_integration_issue

        notify_integration_issue(
            session,
            provider="WhatsApp",
            message=f"No fue posible enviar mensaje a {recipient}: {exc}",
            appointment_id=int(entity_id) if entity_type == "appointment" and entity_id is not None else None,
        )
    except Exception:
        pass
    session.commit()


def _iso_message_time(value: datetime) -> str:
    return value.astimezone(get_timezone()).strftime("%d/%m/%Y %H:%M")


def _send_text_payload(recipient: str, message: str) -> dict:
    clean_recipient = "".join(ch for ch in str(recipient) if ch.isdigit()) or str(recipient).strip()
    return {
        "messaging_product": "whatsapp",
        "to": clean_recipient,
        "type": "text",
        "text": {"body": message},
    }


def send_text_message(
    session,
    *,
    recipient: str,
    message: str,
    integration_account_id: int | None = None,
    company_id: int | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    event_type: str = "message.outbound",
) -> dict:
    payload = _send_text_payload(recipient, message)
    runtime = resolve_provider_account(
        session,
        company_id=company_id,
        provider=IntegrationAccountProvider.WHATSAPP_META.value,
        selected_id=integration_account_id,
    )
    account = runtime.get("integration_account")
    credentials = runtime.get("credentials") or {}
    config = runtime.get("config") or {}

    if runtime.get("source") == "none":
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.WHATSAPP_META.value,
            integration_account_id=integration_account_id,
            event_type=event_type,
            status=IntegrationStatus.SKIPPED.value,
            entity_type=entity_type,
            entity_id=entity_id,
            request_payload=payload,
            error_message="WhatsApp no configurado para esta empresa.",
        )
        session.commit()
        return {"delivered": False, "external_message_id": None, "error": "WhatsApp no configurado."}

    url = f"{GRAPH_API_URL}/{config.get('api_version', 'v20.0')}/{config.get('phone_number_id')}/messages"
    headers = {
        "Authorization": f"Bearer {credentials.get('access_token', '')}",
        "Content-Type": "application/json",
    }
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=20.0)
        response.raise_for_status()
        data = response.json()
        external_message_id = None
        messages = data.get("messages") or []
        if messages:
            external_message_id = messages[0].get("id")
        if account:
            log_usage(session, account.id)
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.WHATSAPP_META.value,
            integration_account_id=account.id if account else None,
            event_type=event_type,
            status=IntegrationStatus.SUCCESS.value,
            entity_type=entity_type,
            entity_id=entity_id,
            external_id=external_message_id,
            request_payload=payload,
            response_payload=data,
        )
        session.commit()
        return {
            "delivered": True,
            "external_message_id": external_message_id,
            "response_payload": data,
            "integration_account_id": account.id if account else None,
        }
    except httpx.HTTPStatusError as exc:  # pragma: no cover - external API branch
        if account and exc.response.status_code == 401:
            handle_expired_credentials(session, account.id, error_message=str(exc))
        _log_and_notify_failure(session, exc, account, event_type, entity_type, entity_id, payload, recipient)
        return {"delivered": False, "external_message_id": None, "error": str(exc)}
    except httpx.RequestError as exc:  # pragma: no cover - network error branch
        _log_and_notify_failure(session, exc, account, event_type, entity_type, entity_id, payload, recipient)
        return {"delivered": False, "external_message_id": None, "error": str(exc)}


def send_appointment_confirmation(session, appointment, recipient: str) -> dict:
    message = (
        f"Tu cita esta confirmada para {_iso_message_time(appointment.scheduled_start)}. "
        f"Servicio: {appointment.service.name if appointment.service else 'Servicio'}. "
        f"Te esperamos en Torqly."
    )
    return send_text_message(
        session,
        recipient=recipient,
        message=message,
        integration_account_id=getattr(appointment, "whatsapp_integration_id", None),
        entity_type="appointment",
        entity_id=appointment.id,
        event_type="appointment.notification",
    )


def send_appointment_cancellation(session, appointment, recipient: str) -> dict:
    service_name = appointment.service.name if appointment.service else "tu servicio"
    message = (
        f"Tu cita de {service_name} para {_iso_message_time(appointment.scheduled_start)} "
        "ha sido cancelada. Si deseas reagendar, responde a este mensaje."
    )
    return send_text_message(
        session,
        recipient=recipient,
        message=message,
        integration_account_id=getattr(appointment, "whatsapp_integration_id", None),
        entity_type="appointment",
        entity_id=appointment.id,
        event_type="appointment.cancellation",
    )


def send_service_completed(session, appointment, recipient: str) -> dict:
    message = (
        f"Tu servicio {appointment.service.name if appointment.service else ''} fue marcado como terminado. "
        "Gracias por confiar en Torqly."
    ).strip()
    return send_text_message(
        session,
        recipient=recipient,
        message=message,
        integration_account_id=getattr(appointment, "whatsapp_integration_id", None),
        entity_type="appointment",
        entity_id=appointment.id,
        event_type="appointment.completed",
    )
