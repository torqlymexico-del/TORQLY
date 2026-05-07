from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Appointment
from app.services.service_jobs import finish_task_from_clickup


FINISHED_STATUSES = {
    "complete",
    "completed",
    "done",
    "closed",
    "terminado",
    "finished",
}


def _extract_status_value(payload: dict) -> str | None:
    history_items = payload.get("history_items") or [{}]
    first_history = history_items[0] if history_items else {}
    candidates = [
        payload.get("status"),
        payload.get("task_status"),
        first_history.get("after", {}).get("status"),
        first_history.get("after", {}).get("name"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().lower()
    return None


def process_clickup_webhook(session: Session, payload: dict) -> dict:
    event_name = payload.get("event")
    task_id = str(payload.get("task_id") or payload.get("task", {}).get("id") or "").strip()
    if not task_id:
        return {"matched": False, "event": event_name, "completed": False, "integration_account_id": None}

    appointment = session.scalar(
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.vehicle),
            joinedload(Appointment.service),
            joinedload(Appointment.operator),
            joinedload(Appointment.service_job),
        )
        .where(Appointment.clickup_task_id == task_id)
        .where(Appointment.deleted_at.is_(None))
    )
    if not appointment:
        return {
            "matched": False,
            "event": event_name,
            "completed": False,
            "integration_account_id": None,
        }

    normalized_status = _extract_status_value(payload)
    if event_name == "taskStatusUpdated" and normalized_status in FINISHED_STATUSES:
        updated = finish_task_from_clickup(session, appointment, payload=payload)
        return {
            "matched": True,
            "event": event_name,
            "completed": True,
            "appointment_id": updated.id,
            "integration_account_id": updated.clickup_integration_id,
        }

    return {
        "matched": True,
        "event": event_name,
        "completed": False,
        "appointment_id": appointment.id,
        "integration_account_id": appointment.clickup_integration_id,
    }
