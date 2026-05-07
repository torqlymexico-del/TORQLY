from __future__ import annotations

import httpx

from app.enums import AppointmentStatus, IntegrationAccountProvider, IntegrationStatus
from app.services.audit import log_integration_event
from app.services.external_sync import upsert_external_sync_record
from app.services.integration_manager import (
    handle_expired_credentials,
    log_usage,
    resolve_provider_account,
)


CLICKUP_API_BASE = "https://api.clickup.com/api/v2"


def _runtime_for_appointment(session, appointment) -> dict:
    return resolve_provider_account(
        session,
        company_id=None,
        provider=IntegrationAccountProvider.CLICKUP.value,
        selected_id=getattr(appointment, "clickup_integration_id", None),
    )


def _clickup_headers(runtime: dict) -> dict[str, str]:
    return {
        "Authorization": runtime.get("credentials", {}).get("api_token", ""),
        "Content-Type": "application/json",
    }


def _appointment_status_to_clickup(appointment_status: str) -> str:
    normalized = (appointment_status or "").strip().lower()
    if normalized in {AppointmentStatus.IN_PROGRESS.value, "in progress"}:
        return "in progress"
    if normalized in {AppointmentStatus.FINISHED.value, "complete", "completed", "done"}:
        return "complete"
    if normalized in {AppointmentStatus.CANCELLED.value, "cancelled", "canceled", "closed"}:
        return "closed"
    return "to do"


def _task_url(task_id: str | None) -> str | None:
    return f"https://app.clickup.com/t/{task_id}" if task_id else None


def _task_description(appointment) -> str:
    lines = [
        f"Cita Torqly #{appointment.id}",
        f"Cliente: {appointment.client.name if appointment.client else appointment.client_id}",
        (
            f"Vehiculo: {appointment.vehicle.brand} {appointment.vehicle.model}"
            if appointment.vehicle
            else f"Vehiculo: {appointment.vehicle_id}"
        ),
        f"Servicio: {appointment.service.name if appointment.service else appointment.service_catalog_id}",
        f"Fecha: {appointment.scheduled_start.isoformat()}",
        f"Estado: {appointment.status}",
        f"Origen: {appointment.origin}",
    ]
    if appointment.operator:
        lines.append(f"Operador: {appointment.operator.name}")
    if appointment.address:
        lines.append(f"Direccion: {appointment.address}")
    if appointment.notes:
        lines.append(f"Notas: {appointment.notes}")
    return "\n".join(lines)


def _task_payload(appointment, *, include_status: bool = True, for_update: bool = False) -> dict:
    payload: dict = {
        "name": (
            f"{appointment.service.name if appointment.service else 'Servicio'} - "
            f"{appointment.client.name if appointment.client else appointment.client_id}"
        ),
        "description": _task_description(appointment),
        "notify_all": False,
        "start_date": int(appointment.scheduled_start.timestamp() * 1000),
        "start_date_time": True,
        "due_date": int(appointment.scheduled_start.timestamp() * 1000),
        "due_date_time": True,
    }
    if appointment.service and appointment.service.estimated_duration_minutes:
        payload["time_estimate"] = int(appointment.service.estimated_duration_minutes) * 60 * 1000
    if include_status:
        payload["status"] = _appointment_status_to_clickup(appointment.status)
    clickup_user_id = getattr(appointment.operator, "clickup_user_id", None) if appointment.operator else None
    if clickup_user_id and str(clickup_user_id).isdigit():
        payload["assignees"] = (
            {"add": [int(clickup_user_id)], "rem": []} if for_update else [int(clickup_user_id)]
        )
    return payload


def _notify_clickup_failure(session, *, message: str, appointment_id: int | None = None) -> None:
    try:
        from app.services.notifications import notify_integration_issue

        notify_integration_issue(
            session,
            provider="ClickUp",
            message=message,
            appointment_id=appointment_id,
        )
    except Exception:
        pass


def verify_clickup_signature(body: bytes, signature_header: str | None) -> bool:
    from app.database import SessionLocal
    from app.services.integration_manager import verify_clickup_signature as verify_multi_signature

    with SessionLocal() as session:
        return verify_multi_signature(session, body=body, signature_header=signature_header)


def create_clickup_task(session, appointment) -> dict | None:
    runtime = _runtime_for_appointment(session, appointment)
    account = runtime.get("integration_account")
    config = runtime.get("config") or {}
    if runtime.get("source") == "none":
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.CLICKUP.value,
            integration_account_id=getattr(appointment, "clickup_integration_id", None),
            event_type="appointment.create",
            status=IntegrationStatus.SKIPPED.value,
            entity_type="appointment",
            entity_id=appointment.id,
            error_message="ClickUp no configurado.",
        )
        session.commit()
        return None
    payload = _task_payload(appointment, for_update=True)
    url = f"{CLICKUP_API_BASE}/list/{config.get('list_id')}/task"
    try:
        response = httpx.post(url, headers=_clickup_headers(runtime), json=payload, timeout=20.0)
        response.raise_for_status()
        data = response.json()
        task_id = data.get("id")
        task_url = data.get("url") or _task_url(task_id)
        if account:
            log_usage(session, account.id)
        upsert_external_sync_record(
            session,
            provider=IntegrationAccountProvider.CLICKUP.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=task_id,
            integration_account_id=account.id if account else None,
            sync_status="success",
        )
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.CLICKUP.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.create",
            status=IntegrationStatus.SUCCESS.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=task_id,
            request_payload=payload,
            response_payload=data,
        )
        session.commit()
        return {"id": task_id, "url": task_url}
    except Exception as exc:  # pragma: no cover - external API branch
        if account and "401" in str(exc):
            handle_expired_credentials(session, account.id, error_message=str(exc))
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.CLICKUP.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.create",
            status=IntegrationStatus.FAILED.value,
            entity_type="appointment",
            entity_id=appointment.id,
            request_payload=payload,
            error_message=str(exc),
        )
        _notify_clickup_failure(
            session,
            message=f"No fue posible crear tarea ClickUp para la cita {appointment.id}: {exc}",
            appointment_id=appointment.id,
        )
        session.commit()
        return None


def get_clickup_task(session, task_id: str, *, integration_account_id: int | None = None) -> dict | None:
    runtime = resolve_provider_account(
        session,
        company_id=None,
        provider=IntegrationAccountProvider.CLICKUP.value,
        selected_id=integration_account_id,
    )
    account = runtime.get("integration_account")
    if runtime.get("source") == "none" or not task_id:
        return None
    url = f"{CLICKUP_API_BASE}/task/{task_id}"
    try:
        response = httpx.get(url, headers=_clickup_headers(runtime), timeout=20.0)
        response.raise_for_status()
        if account:
            log_usage(session, account.id)
        return response.json()
    except Exception as exc:  # pragma: no cover - external API branch
        if account and "401" in str(exc):
            handle_expired_credentials(session, account.id, error_message=str(exc))
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.CLICKUP.value,
            integration_account_id=account.id if account else None,
            event_type="task.fetch",
            status=IntegrationStatus.FAILED.value,
            entity_type="appointment",
            entity_id=None,
            external_id=task_id,
            error_message=str(exc),
        )
        session.commit()
        return None


def update_clickup_task(session, appointment) -> dict | None:
    runtime = _runtime_for_appointment(session, appointment)
    account = runtime.get("integration_account")
    if runtime.get("source") == "none":
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.CLICKUP.value,
            integration_account_id=getattr(appointment, "clickup_integration_id", None),
            event_type="appointment.update",
            status=IntegrationStatus.SKIPPED.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=appointment.clickup_task_id,
            error_message="ClickUp no configurado.",
        )
        session.commit()
        return None

    if not appointment.clickup_task_id:
        return create_clickup_task(session, appointment)

    payload = _task_payload(appointment)
    url = f"{CLICKUP_API_BASE}/task/{appointment.clickup_task_id}"
    try:
        response = httpx.put(url, headers=_clickup_headers(runtime), json=payload, timeout=20.0)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # pragma: no cover - external API branch
        try:
            retry_payload = _task_payload(appointment, include_status=False, for_update=True)
            response = httpx.put(url, headers=_clickup_headers(runtime), json=retry_payload, timeout=20.0)
            response.raise_for_status()
            data = response.json()
            payload = retry_payload
        except Exception as retry_exc:
            if "404" in str(retry_exc):
                return create_clickup_task(session, appointment)
            if account and "401" in str(retry_exc):
                handle_expired_credentials(session, account.id, error_message=str(retry_exc))
            log_integration_event(
                session,
                provider=IntegrationAccountProvider.CLICKUP.value,
                integration_account_id=account.id if account else None,
                event_type="appointment.update",
                status=IntegrationStatus.FAILED.value,
                entity_type="appointment",
                entity_id=appointment.id,
                external_id=appointment.clickup_task_id,
                request_payload=payload,
                error_message=str(retry_exc),
            )
            upsert_external_sync_record(
                session,
                provider=IntegrationAccountProvider.CLICKUP.value,
                entity_type="appointment",
                entity_id=appointment.id,
                external_id=appointment.clickup_task_id,
                integration_account_id=account.id if account else None,
                sync_status="error",
                error_message=str(retry_exc),
            )
            _notify_clickup_failure(
                session,
                message=f"No fue posible actualizar tarea ClickUp de la cita {appointment.id}: {retry_exc}",
                appointment_id=appointment.id,
            )
            session.commit()
            return None

    task_id = data.get("id") or appointment.clickup_task_id
    task_url = data.get("url") or _task_url(task_id)
    if account:
        log_usage(session, account.id)
    upsert_external_sync_record(
        session,
        provider=IntegrationAccountProvider.CLICKUP.value,
        entity_type="appointment",
        entity_id=appointment.id,
        external_id=task_id,
        integration_account_id=account.id if account else None,
        sync_status="success",
    )
    log_integration_event(
        session,
        provider=IntegrationAccountProvider.CLICKUP.value,
        integration_account_id=account.id if account else None,
        event_type="appointment.update",
        status=IntegrationStatus.SUCCESS.value,
        entity_type="appointment",
        entity_id=appointment.id,
        external_id=task_id,
        request_payload=payload,
        response_payload=data,
    )
    session.commit()
    return {"id": task_id, "url": task_url}
