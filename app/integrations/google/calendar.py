from datetime import timedelta

from app.config import settings
from app.enums import AppointmentStatus, IntegrationAccountProvider, IntegrationStatus
from app.integrations.google.auth import (
    load_google_credentials,
    load_google_credentials_from_runtime,
)
from app.services.audit import log_integration_event
from app.services.external_sync import upsert_external_sync_record
from app.services.integration_manager import (
    handle_expired_credentials,
    log_usage,
    resolve_provider_account,
)
from app.utils.dates import get_timezone


def _get_calendar_service(session, appointment):
    integration_account_id = getattr(appointment, "google_calendar_integration_id", None)
    runtime = resolve_provider_account(
        session,
        company_id=None,
        provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
        selected_id=integration_account_id,
    )
    account = runtime.get("integration_account")
    if runtime.get("source") == "database":
        credentials, error = load_google_credentials_from_runtime(
            credentials=runtime.get("credentials") or {},
            config=runtime.get("config") or {},
            scopes=settings.google_calendar_scope_list,
        )
    elif runtime.get("source") == "settings":
        credentials, error = load_google_credentials()
    else:
        credentials, error = None, "Google Calendar no configurado para esta cita."
    if error:
        return None, error, runtime
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return None, "Las dependencias de Google no estan instaladas.", runtime
    if account:
        log_usage(session, account.id)
    return build("calendar", "v3", credentials=credentials, cache_discovery=False), None, runtime


def _appointment_time_bounds(appointment):
    start = appointment.scheduled_start
    if start.tzinfo is None:
        start = start.replace(tzinfo=get_timezone())
    duration = appointment.service.estimated_duration_minutes if appointment.service else 60
    end = start + timedelta(minutes=duration)
    return start, end


def _event_payload(appointment) -> dict:
    start, end = _appointment_time_bounds(appointment)
    client_name = appointment.client.name if appointment.client else f"Cliente {appointment.client_id}"
    vehicle_label = (
        f"{appointment.vehicle.brand} {appointment.vehicle.model}"
        if appointment.vehicle
        else f"Vehiculo {appointment.vehicle_id}"
    )
    operator_name = appointment.operator.name if appointment.operator else "Sin asignar"
    service_name = appointment.service.name if appointment.service else f"Servicio {appointment.service_catalog_id}"
    description_lines = [
        f"Cliente: {client_name}",
        f"Vehiculo: {vehicle_label}",
        f"Servicio: {service_name}",
        f"Operador: {operator_name}",
        f"Estado: {appointment.status}",
    ]
    if appointment.notes:
        description_lines.append(f"Notas: {appointment.notes}")

    return {
        "summary": f"{service_name} - {client_name}",
        "description": "\n".join(description_lines),
        "location": appointment.address or "",
        "start": {"dateTime": start.isoformat(), "timeZone": settings.timezone},
        "end": {"dateTime": end.isoformat(), "timeZone": settings.timezone},
        "status": "cancelled" if appointment.status == AppointmentStatus.CANCELLED.value else "confirmed",
        "extendedProperties": {
            "private": {
                "appointment_id": str(appointment.id),
                "operator_id": str(appointment.operator_id or ""),
                "charge_status": str(getattr(appointment, "charge_status", "")),
            }
        },
    }


def create_calendar_event(session, appointment) -> str | None:
    service, error, runtime = _get_calendar_service(session, appointment)
    account = runtime.get("integration_account")
    config = runtime.get("config") or {}
    if error:
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.create",
            status=IntegrationStatus.SKIPPED.value,
            entity_type="appointment",
            entity_id=appointment.id,
            error_message=error,
        )
        session.commit()
        return None

    payload = _event_payload(appointment)
    try:
        response = (
            service.events()
            .insert(
                calendarId=config.get("calendar_id") or settings.google_calendar_id,
                body=payload,
                sendUpdates=settings.google_calendar_send_updates,
            )
            .execute()
        )
        event_id = response.get("id")
        upsert_external_sync_record(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=event_id,
            integration_account_id=account.id if account else None,
            sync_status="success",
        )
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.create",
            status=IntegrationStatus.SUCCESS.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=event_id,
            request_payload=payload,
            response_payload={"htmlLink": response.get("htmlLink")},
        )
        session.commit()
        return event_id
    except Exception as exc:  # pragma: no cover - external API branch
        if account and "401" in str(exc):
            handle_expired_credentials(session, account.id, error_message=str(exc))
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.create",
            status=IntegrationStatus.FAILED.value,
            entity_type="appointment",
            entity_id=appointment.id,
            request_payload=payload,
            error_message=str(exc),
        )
        upsert_external_sync_record(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=appointment.google_event_id or f"appointment-{appointment.id}",
            integration_account_id=account.id if account else None,
            sync_status="error",
            error_message=str(exc),
        )
        session.commit()
        return None


def update_calendar_event(session, appointment) -> str | None:
    service, error, runtime = _get_calendar_service(session, appointment)
    account = runtime.get("integration_account")
    config = runtime.get("config") or {}
    if error:
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.update",
            status=IntegrationStatus.SKIPPED.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=appointment.google_event_id,
            error_message=error,
        )
        session.commit()
        return None

    if appointment.status == AppointmentStatus.CANCELLED.value:
        cancel_calendar_event(session, appointment)
        return appointment.google_event_id

    if not appointment.google_event_id:
        return create_calendar_event(session, appointment)

    payload = _event_payload(appointment)
    try:
        response = (
            service.events()
            .update(
                calendarId=config.get("calendar_id") or settings.google_calendar_id,
                eventId=appointment.google_event_id,
                body=payload,
                sendUpdates=settings.google_calendar_send_updates,
            )
            .execute()
        )
        event_id = response.get("id")
        upsert_external_sync_record(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=event_id,
            integration_account_id=account.id if account else None,
            sync_status="success",
        )
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.update",
            status=IntegrationStatus.SUCCESS.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=event_id,
            request_payload=payload,
            response_payload={"htmlLink": response.get("htmlLink")},
        )
        session.commit()
        return event_id
    except Exception as exc:  # pragma: no cover - external API branch
        if "404" in str(exc):
            return create_calendar_event(session, appointment)
        if account and "401" in str(exc):
            handle_expired_credentials(session, account.id, error_message=str(exc))
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.update",
            status=IntegrationStatus.FAILED.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=appointment.google_event_id,
            request_payload=payload,
            error_message=str(exc),
        )
        upsert_external_sync_record(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=appointment.google_event_id,
            integration_account_id=account.id if account else None,
            sync_status="error",
            error_message=str(exc),
        )
        session.commit()
        return None


def cancel_calendar_event(session, appointment) -> None:
    service, error, runtime = _get_calendar_service(session, appointment)
    account = runtime.get("integration_account")
    config = runtime.get("config") or {}
    if error:
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.cancel",
            status=IntegrationStatus.SKIPPED.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=appointment.google_event_id,
            error_message=error,
        )
        session.commit()
        return

    if not appointment.google_event_id:
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.cancel",
            status=IntegrationStatus.SKIPPED.value,
            entity_type="appointment",
            entity_id=appointment.id,
            error_message="La cita no tiene google_event_id para cancelar.",
        )
        session.commit()
        return

    try:
        service.events().delete(
            calendarId=config.get("calendar_id") or settings.google_calendar_id,
            eventId=appointment.google_event_id,
            sendUpdates=settings.google_calendar_send_updates,
        ).execute()
        upsert_external_sync_record(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=appointment.google_event_id,
            integration_account_id=account.id if account else None,
            sync_status="cancelled",
        )
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.cancel",
            status=IntegrationStatus.SUCCESS.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=appointment.google_event_id,
        )
        session.commit()
    except Exception as exc:  # pragma: no cover - external API branch
        status = IntegrationStatus.SUCCESS.value if "404" in str(exc) else IntegrationStatus.FAILED.value
        if account and "401" in str(exc):
            handle_expired_credentials(session, account.id, error_message=str(exc))
        upsert_external_sync_record(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=appointment.google_event_id,
            integration_account_id=account.id if account else None,
            sync_status="cancelled" if status == IntegrationStatus.SUCCESS.value else "error",
            error_message=None if status == IntegrationStatus.SUCCESS.value else str(exc),
        )
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            integration_account_id=account.id if account else None,
            event_type="appointment.cancel",
            status=status,
            entity_type="appointment",
            entity_id=appointment.id,
            external_id=appointment.google_event_id,
            error_message=None if status == IntegrationStatus.SUCCESS.value else str(exc),
        )
        session.commit()
