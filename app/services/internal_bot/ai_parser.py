from __future__ import annotations

import json
import logging

from app.enums import InternalBotIntent
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Intent catalogue sent to the model ───────────────────────────────────────

_INTENTS_DOC = """
get_today_agenda           - Ver las citas/agenda/servicios de hoy
get_today_sales            - Ver ventas/ingresos/cobros de hoy
get_today_cash_cut         - Ver corte de caja / efectivo del día
get_operator_tasks         - Ver tareas/servicios de un operador (param: operator_name)
get_pending_services       - Ver servicios pendientes/sin iniciar hoy
get_in_progress_services   - Ver servicios en proceso/en curso ahora
get_finished_services      - Ver servicios terminados/completados hoy
get_today_commissions      - Ver comisiones de todos los operadores de hoy
get_operator_commissions   - Ver comisiones de un operador específico (param: operator_name)
reassign_operator          - Reasignar servicio a otro operador (params: vehicle_query, operator_name)
finish_service             - Marcar servicio como terminado (param: appointment_id como entero)
create_appointment         - Crear cita (params: schedule_label="hoy"|"mañana"|"DD/MM/YYYY", time_label="HH:MM", details="servicio + vehículo")
unknown                    - El comando no corresponde a ninguna acción disponible
"""

_CLASSIFY_SYSTEM = f"""Eres un clasificador de intents para un sistema de administración de taller de lavado y detallado automotriz en México.

Dado un mensaje en español, determina cuál de los siguientes intents corresponde y extrae los parámetros necesarios:

{_INTENTS_DOC}

Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional ni markdown.
Formato: {{"intent": "<intent>", "params": {{<parámetros requeridos o vacío>}}}}

Ejemplos:
- "¿Cuántas citas hay hoy?" → {{"intent": "get_today_agenda", "params": {{}}}}
- "¿Cuáles son las ventas?" → {{"intent": "get_today_sales", "params": {{}}}}
- "Tareas de Carlos" → {{"intent": "get_operator_tasks", "params": {{"operator_name": "Carlos"}}}}
- "Reasigna el Corolla a Pedro" → {{"intent": "reassign_operator", "params": {{"vehicle_query": "Corolla", "operator_name": "Pedro"}}}}
- "¿Qué hora es?" → {{"intent": "unknown", "params": {{}}}}"""

_FREEFORM_SYSTEM = """Eres el asistente interno de un taller de lavado y detallado automotriz en México.
Tienes acceso al resumen operacional del día. Responde de forma concisa y clara en español.
Si no puedes responder con el contexto disponible, dilo directamente.
No inventes datos que no estén en el contexto."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_client():
    """Lazy-load Groq client so the app starts without the key configured."""
    from groq import Groq
    from app.config import settings
    if not settings.groq_api_key:
        return None, None
    return Groq(api_key=settings.groq_api_key), settings.groq_bot_model


def _coerce_params(intent: str, params: dict) -> dict:
    """Ensure param types match what the handlers expect."""
    if intent == InternalBotIntent.FINISH_SERVICE.value and "appointment_id" in params:
        try:
            params["appointment_id"] = int(params["appointment_id"])
        except (ValueError, TypeError):
            pass
    for key in ("operator_name", "vehicle_query", "schedule_label", "time_label", "details"):
        if key in params and not isinstance(params[key], str):
            params[key] = str(params[key])
    return params


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── Public API ────────────────────────────────────────────────────────────────

def is_available() -> bool:
    from app.config import settings
    return bool(settings.groq_api_key)


def classify_intent(command: str) -> dict | None:
    """
    Ask the LLM to classify the command into an intent + params dict.
    Returns None if AI is unavailable or the call fails.
    """
    client, model = _get_client()
    if client is None:
        return None
    try:
        completion = client.chat.completions.create(
            model=model,
            max_tokens=200,
            temperature=0,
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user", "content": command},
            ],
        )
        raw = completion.choices[0].message.content or ""
        data = _extract_json(raw)
        intent = str(data.get("intent", "unknown"))
        valid_intents = {i.value for i in InternalBotIntent}
        if intent not in valid_intents:
            intent = InternalBotIntent.UNKNOWN.value
        params = _coerce_params(intent, data.get("params") or {})
        return {"intent": intent, "params": params}
    except Exception as exc:
        logger.warning("Groq intent classification failed: %s", exc)
        return None


def answer_freeform(command: str, context_snapshot: str) -> str | None:
    """
    Ask the LLM to answer freely using a snapshot of current operational data.
    Returns None if AI is unavailable or the call fails.
    """
    client, model = _get_client()
    if client is None:
        return None
    try:
        completion = client.chat.completions.create(
            model=model,
            max_tokens=512,
            temperature=0.3,
            messages=[
                {"role": "system", "content": _FREEFORM_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Datos actuales del sistema:\n{context_snapshot}\n\n"
                        f"Pregunta: {command}"
                    ),
                },
            ],
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("Groq freeform answer failed: %s", exc)
        return None
