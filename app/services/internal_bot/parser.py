from __future__ import annotations

import re
import unicodedata

from app.enums import InternalBotIntent


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    plain = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(plain.lower().strip().split())


def parse_command(command: str) -> dict:
    normalized = normalize_text(command)

    if normalized == "agenda de hoy":
        return {"intent": InternalBotIntent.GET_TODAY_AGENDA.value, "params": {}}
    if normalized == "ventas de hoy":
        return {"intent": InternalBotIntent.GET_TODAY_SALES.value, "params": {}}
    if normalized == "corte de hoy":
        return {"intent": InternalBotIntent.GET_TODAY_CASH_CUT.value, "params": {}}
    if normalized == "servicios pendientes":
        return {"intent": InternalBotIntent.GET_PENDING_SERVICES.value, "params": {}}
    if normalized == "servicios en proceso":
        return {"intent": InternalBotIntent.GET_IN_PROGRESS_SERVICES.value, "params": {}}
    if normalized == "servicios terminados":
        return {"intent": InternalBotIntent.GET_FINISHED_SERVICES.value, "params": {}}
    if normalized == "comisiones de hoy":
        return {"intent": InternalBotIntent.GET_TODAY_COMMISSIONS.value, "params": {}}

    operator_tasks = re.match(r"^tareas de (?P<operator>.+)$", normalized)
    if operator_tasks:
        return {
            "intent": InternalBotIntent.GET_OPERATOR_TASKS.value,
            "params": {"operator_name": operator_tasks.group("operator").strip()},
        }

    operator_commissions = re.match(r"^comisiones de (?P<operator>.+)$", normalized)
    if operator_commissions:
        return {
            "intent": InternalBotIntent.GET_OPERATOR_COMMISSIONS.value,
            "params": {"operator_name": operator_commissions.group("operator").strip()},
        }

    reassign = re.match(r"^reasigna(?:r)? (?:el |la )?(?P<vehicle>.+?) a (?P<operator>.+)$", normalized)
    if reassign:
        return {
            "intent": InternalBotIntent.REASSIGN_OPERATOR.value,
            "params": {
                "vehicle_query": reassign.group("vehicle").strip(),
                "operator_name": reassign.group("operator").strip(),
            },
        }

    finish = re.match(r"^marca terminado el servicio (?P<appointment_id>\d+)$", normalized)
    if finish:
        return {
            "intent": InternalBotIntent.FINISH_SERVICE.value,
            "params": {"appointment_id": int(finish.group("appointment_id"))},
        }

    create_appointment = re.match(
        r"^crea cita para (?P<schedule>.+?) a las? (?P<time>\d{1,2}(?::\d{2})?) (?P<details>.+)$",
        normalized,
    )
    if create_appointment:
        return {
            "intent": InternalBotIntent.CREATE_APPOINTMENT.value,
            "params": {
                "schedule_label": create_appointment.group("schedule").strip(),
                "time_label": create_appointment.group("time").strip(),
                "details": create_appointment.group("details").strip(),
            },
        }

    return {"intent": InternalBotIntent.UNKNOWN.value, "params": {}}
