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
get_analytics              - Consultas históricas: día más concurrido, servicio más vendido, totales semanales/mensuales (param: question - la pregunta original del usuario)
get_navigation_help        - Orientar sobre dónde está algo en el panel: dar de alta usuarios, eliminar registros, configurar algo (param: question - la pregunta original del usuario)
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
- "¿Qué día se lavaron más autos?" → {{"intent": "get_analytics", "params": {{"question": "¿Qué día se lavaron más autos?"}}}}
- "¿Cuál es el servicio más vendido?" → {{"intent": "get_analytics", "params": {{"question": "¿Cuál es el servicio más vendido?"}}}}
- "¿Dónde doy de alta a un lavador?" → {{"intent": "get_navigation_help", "params": {{"question": "¿Dónde doy de alta a un lavador?"}}}}
- "¿Cómo elimino una cuenta de crédito?" → {{"intent": "get_navigation_help", "params": {{"question": "¿Cómo elimino una cuenta de crédito?"}}}}
- "¿Qué hora es?" → {{"intent": "unknown", "params": {{}}}}"""

_FREEFORM_SYSTEM = """Eres el asistente interno de un taller de lavado y detallado automotriz en México.
Tienes acceso al resumen operacional del día. Responde de forma concisa y clara en español.
Si no puedes responder con el contexto disponible, dilo directamente.
No inventes datos que no estén en el contexto."""

_ANALYTICS_SYSTEM = """Eres el asistente de análisis de un taller de lavado y detallado automotriz en México.
Tienes acceso a datos históricos del negocio. Analiza los datos y responde la pregunta del usuario
de forma concisa, clara y útil en español. Destaca los números más importantes."""

# ── Navigation knowledge base ─────────────────────────────────────────────────

_NAV_KNOWLEDGE = """
MAPA DE NAVEGACIÓN DEL PANEL TORQLY:

USUARIOS Y EQUIPO:
- Dar de alta un lavador/operador → Menú lateral > Equipo > Usuarios > botón "Nuevo usuario" > seleccionar rol "Operador"
- Dar de alta un supervisor → Menú lateral > Equipo > Usuarios > botón "Nuevo usuario" > seleccionar rol "Supervisor"
- Ver todos los usuarios → Menú lateral > Equipo > Usuarios
- Editar un usuario → Equipo > Usuarios > clic en el usuario > botón "Editar"
- Desactivar/eliminar usuario → Equipo > Usuarios > clic en el usuario > botón "Desactivar"
- Cambiar contraseña de usuario → Equipo > Usuarios > clic en el usuario > "Cambiar contraseña"

CLIENTES Y VEHÍCULOS:
- Dar de alta un cliente → Menú lateral > Clientes > botón "Nuevo cliente"
- Buscar cliente → Clientes > barra de búsqueda por nombre o teléfono
- Ver vehículos de un cliente → Clientes > clic en el cliente > pestaña "Vehículos"
- Agregar vehículo → Clientes > clic en cliente > Vehículos > "Agregar vehículo"
- Editar vehículo → Clientes > clic en cliente > Vehículos > clic en vehículo > "Editar"

CITAS Y AGENDA:
- Ver agenda del día → Menú lateral > Agenda
- Crear nueva cita → Agenda > botón "Nueva cita"
- Cancelar una cita → Agenda > clic en la cita > botón "Cancelar"
- Reagendar una cita → Agenda > clic en la cita > "Editar" > cambiar fecha/hora
- Ver citas por operador → Agenda > filtro "Operador"

SERVICIOS Y CATÁLOGO:
- Agregar servicio al catálogo → Menú lateral > Catálogo > botón "Nuevo servicio"
- Editar precio de un servicio → Catálogo > clic en el servicio > "Editar" > cambiar precio
- Desactivar servicio → Catálogo > clic en el servicio > "Desactivar"
- Ver servicios por categoría → Catálogo > filtro "Categoría"

CAJA Y COBROS:
- Ver corte de caja → Menú lateral > Caja > Cortes
- Hacer corte de caja → Caja > Cortes > botón "Nuevo corte"
- Ver ventas del día → Caja > Ventas o Menú lateral > Reportes > Diario
- Registrar pago de una cita → Agenda > clic en la cita > "Registrar pago"

CRÉDITOS:
- Ver cuentas de crédito → Menú lateral > Créditos
- Crear cuenta de crédito → Créditos > botón "Nueva cuenta"
- Eliminar/cerrar cuenta de crédito → Créditos > clic en la cuenta > botón "Eliminar" o "Cerrar"
- Registrar abono → Créditos > clic en la cuenta > "Registrar abono"
- Ver historial de abonos → Créditos > clic en la cuenta > pestaña "Historial"

COMISIONES Y NÓMINA:
- Ver comisiones del día → Menú lateral > Comisiones
- Ver comisiones por operador → Comisiones > filtro por operador
- Ver nómina → Menú lateral > Nómina
- Generar nómina → Nómina > botón "Generar nómina"

INVENTARIO:
- Ver inventario → Menú lateral > Inventario
- Agregar producto → Inventario > botón "Nuevo producto"
- Registrar entrada de stock → Inventario > clic en producto > "Registrar entrada"
- Ver productos con stock bajo → Inventario > filtro "Stock bajo"

REPORTES:
- Reporte diario → Menú lateral > Reportes > Diario
- Reporte semanal → Reportes > Semanal
- Reporte de servicios → Reportes > Servicios
- Exportar a Google Sheets → Reportes > botón "Exportar a Sheets"

INTEGRACIONES:
- Configurar WhatsApp → Menú lateral > Integraciones > WhatsApp
- Configurar Google Calendar → Integraciones > Google Calendar
- Ver estado de integraciones → Integraciones > pestaña "Estado"

CONFIGURACIÓN:
- Configurar horario del negocio → Configuración > Horarios
- Cambiar nombre del negocio → Configuración > Información general
- Configurar sucursales → Configuración > Sucursales
"""

_NAV_SYSTEM = f"""Eres el asistente de navegación del panel Torqly, un sistema de gestión para talleres de lavado y detallado automotriz.

Tienes acceso al mapa completo de navegación del panel. Cuando el usuario pregunte dónde está algo o cómo hacer algo en el sistema, responde con los pasos exactos basándote en este mapa:

{_NAV_KNOWLEDGE}

Responde de forma concisa y directa. Si la función no está en el mapa, dilo honestamente.
Responde siempre en español."""


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
    for key in ("operator_name", "vehicle_query", "schedule_label", "time_label", "details", "question"):
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
    """Ask the LLM to classify the command into an intent + params dict."""
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
    """Ask the LLM to answer freely using a snapshot of current operational data."""
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


def answer_analytics(question: str, analytics_data: str) -> str | None:
    """Ask the LLM to interpret historical analytics data and answer the question."""
    client, model = _get_client()
    if client is None:
        return None
    try:
        completion = client.chat.completions.create(
            model=model,
            max_tokens=512,
            temperature=0.2,
            messages=[
                {"role": "system", "content": _ANALYTICS_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Datos históricos del negocio:\n{analytics_data}\n\n"
                        f"Pregunta: {question}"
                    ),
                },
            ],
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("Groq analytics answer failed: %s", exc)
        return None


def answer_navigation(question: str) -> str | None:
    """Answer a navigation/help question about the Torqly panel."""
    client, model = _get_client()
    if client is None:
        return None
    try:
        completion = client.chat.completions.create(
            model=model,
            max_tokens=400,
            temperature=0.1,
            messages=[
                {"role": "system", "content": _NAV_SYSTEM},
                {"role": "user", "content": question},
            ],
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("Groq navigation answer failed: %s", exc)
        return None
