from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, IntegrationLog, User
from app.services.credential_vault import mask_sensitive_payload


def request_ip(request: Request | None) -> str | None:
    if not request:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def log_action(
    session: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: str | int | None,
    description: str | None = None,
    payload: dict | None = None,
    request: Request | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_user_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            description=description,
            payload=mask_sensitive_payload(payload),
            ip_address=request_ip(request),
        )
    )


def log_integration_event(
    session: Session,
    *,
    provider: str,
    integration_account_id: int | None = None,
    event_type: str,
    status: str,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    external_id: str | None = None,
    request_payload: dict | None = None,
    response_payload: dict | None = None,
    error_message: str | None = None,
) -> None:
    session.add(
        IntegrationLog(
            provider=provider,
            integration_account_id=integration_account_id,
            event_type=event_type,
            status=status,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            external_id=external_id,
            request_payload=mask_sensitive_payload(request_payload),
            response_payload=mask_sensitive_payload(response_payload),
            error_message=error_message,
        )
    )
