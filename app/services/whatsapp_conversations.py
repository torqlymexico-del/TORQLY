from __future__ import annotations

from datetime import date, datetime, time, timedelta
import re
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.enums import (
    AppointmentOrigin,
    AppointmentStatus,
    MessageDirection,
    WhatsAppBotState,
    WhatsAppConversationMode,
    WhatsAppConversationStatus,
)
from app.integrations.whatsapp.client import (
    send_appointment_cancellation,
    send_appointment_confirmation,
    send_service_completed,
    send_text_message,
)
from app.integrations.whatsapp.webhook import parse_whatsapp_webhook_payload
from app.models import Client, ServiceCatalog, Vehicle, WhatsAppConversation, WhatsAppMessage
from app.services.audit import log_action
from app.services.exceptions import NotFoundError, ValidationError
from app.services.integration_manager import resolve_whatsapp_account_from_metadata
from app.utils.dates import combine_local_date_time, get_timezone, local_now


AFFIRMATIVE_WORDS = {"si", "sí", "confirmo", "ok", "vale", "listo", "confirmar"}
NEGATIVE_WORDS = {"no", "cambiar", "cancela", "cancelar"}


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    plain = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return plain.lower().strip()


def _clean_phone(phone: str) -> str:
    stripped = "".join(ch for ch in str(phone) if ch.isdigit())
    return stripped or str(phone).strip()


def _payload_data(conversation: WhatsAppConversation) -> dict:
    return dict(conversation.payload or {})


def _set_payload_value(conversation: WhatsAppConversation, **changes) -> None:
    payload = _payload_data(conversation)
    payload.update(changes)
    conversation.payload = payload


def _payload_date(payload: dict, key: str) -> date | None:
    value = payload.get(key)
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _payload_time(payload: dict, key: str) -> time | None:
    value = payload.get(key)
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        try:
            return time.fromisoformat(value)
        except ValueError:
            return None
    return None


def _parse_date_from_text(value: str) -> date | None:
    text = _normalize_text(value)
    today = local_now().date()
    if text in {"hoy"}:
        return today
    if text in {"manana", "mañana", "tomorrow"}:
        return today + timedelta(days=1)

    for pattern, builder in (
        (r"^(\d{4})-(\d{2})-(\d{2})$", lambda m: date(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (r"^(\d{2})/(\d{2})/(\d{4})$", lambda m: date(int(m.group(3)), int(m.group(2)), int(m.group(1)))),
        (r"^(\d{2})/(\d{2})$", lambda m: date(today.year, int(m.group(2)), int(m.group(1)))),
    ):
        match = re.match(pattern, text)
        if not match:
            continue
        try:
            parsed = builder(match)
            if parsed < today and pattern == r"^(\d{2})/(\d{2})$":
                return date(today.year + 1, parsed.month, parsed.day)
            return parsed
        except ValueError:
            return None
    return None


def _parse_time_from_text(value: str) -> time | None:
    match = re.search(r"(\d{1,2}):(\d{2})", value or "")
    if not match:
        return None
    try:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return time(hour=hours, minute=minutes)
    except ValueError:
        return None


def _parse_vehicle_label(vehicle_text: str) -> tuple[str, str]:
    clean = " ".join((vehicle_text or "").split()).strip()
    if not clean:
        return "Vehiculo", "Pendiente"
    parts = clean.split(" ", 1)
    brand = parts[0][:80]
    model = parts[1][:80] if len(parts) > 1 else "General"
    return brand, model


def _format_schedule_for_humans(target_date: date | None, target_time: time | None) -> str:
    if not target_date or not target_time:
        return "fecha pendiente"
    return f"{target_date.strftime('%d/%m/%Y')} a las {target_time.strftime('%H:%M')}"


def _match_service(session: Session, requested_text: str | None) -> ServiceCatalog | None:
    cleaned = _normalize_text(requested_text)
    if not cleaned:
        return None
    services = list(
        session.scalars(
            select(ServiceCatalog)
            .where(ServiceCatalog.deleted_at.is_(None))
            .where(ServiceCatalog.is_active.is_(True))
            .order_by(ServiceCatalog.name.asc())
        ).all()
    )
    if not services:
        return None

    exact = next((item for item in services if _normalize_text(item.name) == cleaned), None)
    if exact:
        return exact

    requested_tokens = {token for token in cleaned.split() if token}
    best_score = -1
    best_item = None
    for item in services:
        haystack = " ".join(
            [
                _normalize_text(item.name),
                _normalize_text(getattr(item, "description", None)),
                _normalize_text(getattr(item, "service_type", None)),
            ]
        )
        score = 0
        for token in requested_tokens:
            if token in haystack:
                score += 1
        if cleaned in haystack:
            score += 3
        if score > best_score:
            best_score = score
            best_item = item
    return best_item if best_score > 0 else None


def _service_prompt(session: Session) -> str:
    services = list(
        session.scalars(
            select(ServiceCatalog.name)
            .where(ServiceCatalog.deleted_at.is_(None))
            .where(ServiceCatalog.is_active.is_(True))
            .order_by(ServiceCatalog.name.asc())
            .limit(6)
        ).all()
    )
    if not services:
        return "Que servicio deseas?"
    return "Que servicio deseas? Opciones: " + ", ".join(services)


def list_conversations(session: Session) -> list[WhatsAppConversation]:
    return list(
        session.scalars(
            select(WhatsAppConversation)
            .options(
                joinedload(WhatsAppConversation.client),
                joinedload(WhatsAppConversation.assigned_admin),
            )
            .order_by(
                WhatsAppConversation.last_message_at.desc().nullslast(),
                WhatsAppConversation.id.desc(),
            )
        ).all()
    )


def get_conversation(session: Session, conversation_id: int) -> WhatsAppConversation:
    conversation = session.scalar(
        select(WhatsAppConversation)
        .options(
            joinedload(WhatsAppConversation.client),
            joinedload(WhatsAppConversation.assigned_admin),
        )
        .where(WhatsAppConversation.id == conversation_id)
    )
    if not conversation:
        raise NotFoundError("Conversacion no encontrada.")
    return conversation


def list_conversation_messages(session: Session, conversation_id: int) -> list[WhatsAppMessage]:
    return list(
        session.scalars(
            select(WhatsAppMessage)
            .where(WhatsAppMessage.conversation_id == conversation_id)
            .order_by(WhatsAppMessage.created_at.asc(), WhatsAppMessage.id.asc())
        ).all()
    )


def _find_client_by_phone(session: Session, phone: str) -> Client | None:
    return session.scalar(
        select(Client)
        .where(Client.deleted_at.is_(None))
        .where(func.replace(Client.phone, " ", "") == phone)
    )


def get_or_create_conversation(
    session: Session,
    *,
    phone: str,
    display_name: str | None = None,
    integration_account_id: int | None = None,
) -> WhatsAppConversation:
    clean_phone = _clean_phone(phone)
    query = (
        select(WhatsAppConversation)
        .where(WhatsAppConversation.phone == clean_phone)
        .where(WhatsAppConversation.status != WhatsAppConversationStatus.ARCHIVED.value)
        .order_by(WhatsAppConversation.last_message_at.desc().nullslast(), WhatsAppConversation.id.desc())
    )
    if integration_account_id is None:
        query = query.where(WhatsAppConversation.integration_account_id.is_(None))
    else:
        query = query.where(WhatsAppConversation.integration_account_id == integration_account_id)
    conversation = session.scalar(query)
    if conversation:
        if display_name and display_name != conversation.display_name:
            conversation.display_name = display_name
        if integration_account_id and not conversation.integration_account_id:
            conversation.integration_account_id = integration_account_id
        if not conversation.client_id:
            existing_client = _find_client_by_phone(session, clean_phone)
            if existing_client:
                conversation.client_id = existing_client.id
        return conversation

    existing_client = _find_client_by_phone(session, clean_phone)
    conversation = WhatsAppConversation(
        phone=clean_phone,
        display_name=display_name,
        client_id=existing_client.id if existing_client else None,
        integration_account_id=integration_account_id,
        mode=WhatsAppConversationMode.BOT.value,
        status=WhatsAppConversationStatus.OPEN.value,
        bot_state=WhatsAppBotState.NEW.value,
        payload={},
    )
    session.add(conversation)
    session.flush()
    return conversation


def _create_message(
    session: Session,
    *,
    conversation: WhatsAppConversation,
    direction: str,
    message_type: str,
    content: str | None,
    external_message_id: str | None,
    payload: dict | None,
    sent_at: datetime | None = None,
    integration_account_id: int | None = None,
) -> WhatsAppMessage:
    message = WhatsAppMessage(
        conversation_id=conversation.id,
        integration_account_id=integration_account_id if integration_account_id is not None else conversation.integration_account_id,
        direction=direction,
        message_type=message_type,
        content=content,
        external_message_id=external_message_id,
        payload=payload,
        sent_at=sent_at,
    )
    session.add(message)
    conversation.last_message_at = sent_at or local_now()
    return message


def _store_inbound_message(session: Session, *, conversation: WhatsAppConversation, event: dict) -> WhatsAppMessage:
    timestamp = event.get("timestamp")
    sent_at = None
    if timestamp:
        try:
            sent_at = datetime.fromtimestamp(int(timestamp), tz=get_timezone())
        except (TypeError, ValueError):
            sent_at = local_now()
    return _create_message(
        session,
        conversation=conversation,
        direction=MessageDirection.INBOUND.value,
        message_type=event.get("message_type", "text"),
        content=event.get("content"),
        external_message_id=event.get("external_message_id"),
        payload=event.get("payload"),
        sent_at=sent_at or local_now(),
        integration_account_id=conversation.integration_account_id,
    )


def _store_outbound_message(
    session: Session,
    *,
    conversation: WhatsAppConversation,
    body: str,
    delivery_result: dict,
) -> WhatsAppMessage:
    payload = {
        "response_payload": delivery_result.get("response_payload"),
        "error": delivery_result.get("error"),
    }
    return _create_message(
        session,
        conversation=conversation,
        direction=MessageDirection.OUTBOUND.value,
        message_type="text",
        content=body,
        external_message_id=delivery_result.get("external_message_id"),
        payload=payload,
        sent_at=local_now(),
        integration_account_id=delivery_result.get("integration_account_id"),
    )


def send_conversation_message(
    session: Session,
    conversation: WhatsAppConversation,
    *,
    body: str,
    actor=None,
    appointment_id: int | None = None,
    integration_account_id: int | None = None,
) -> dict:
    delivery = send_text_message(
        session,
        recipient=conversation.phone,
        message=body,
        integration_account_id=integration_account_id if integration_account_id is not None else conversation.integration_account_id,
        entity_type="appointment" if appointment_id else "conversation",
        entity_id=appointment_id or conversation.id,
        event_type="message.outbound",
    )
    _store_outbound_message(session, conversation=conversation, body=body, delivery_result=delivery)
    if actor is not None:
        log_action(
            session,
            actor=actor,
            action="whatsapp.reply.manual",
            entity_type="conversation",
            entity_id=conversation.id,
            description="Respuesta manual enviada.",
            payload={"delivered": delivery.get("delivered")},
        )
    return delivery


def send_automation_message(
    session: Session,
    *,
    phone: str,
    body: str,
    display_name: str | None = None,
    appointment=None,
    integration_account_id: int | None = None,
) -> dict:
    conversation = get_or_create_conversation(
        session,
        phone=phone,
        display_name=display_name,
        integration_account_id=integration_account_id or getattr(appointment, "whatsapp_integration_id", None),
    )
    if appointment and appointment.client_id and not conversation.client_id:
        conversation.client_id = appointment.client_id
    return send_conversation_message(
        session,
        conversation,
        body=body,
        actor=None,
        appointment_id=appointment.id if appointment else None,
        integration_account_id=integration_account_id or getattr(appointment, "whatsapp_integration_id", None),
    )


def _update_delivery_status(session: Session, event: dict) -> None:
    external_message_id = event.get("external_message_id")
    if not external_message_id:
        return
    message = session.scalar(
        select(WhatsAppMessage).where(WhatsAppMessage.external_message_id == external_message_id)
    )
    if not message:
        return
    timestamp = event.get("timestamp")
    status_time = None
    if timestamp:
        try:
            status_time = datetime.fromtimestamp(int(timestamp), tz=get_timezone())
        except (TypeError, ValueError):
            status_time = local_now()
    if event.get("status") == "delivered":
        message.delivered_at = status_time or local_now()
    elif event.get("status") == "read":
        message.read_at = status_time or local_now()
    payload = dict(message.payload or {})
    payload["status_event"] = event
    message.payload = payload


def _bot_summary(conversation: WhatsAppConversation) -> str:
    payload = _payload_data(conversation)
    return (
        f"Nombre: {payload.get('customer_name')}\n"
        f"Vehiculo: {payload.get('vehicle_text')}\n"
        f"Servicio: {payload.get('service_text')}\n"
        f"Fecha: {_format_schedule_for_humans(_payload_date(payload, 'requested_date'), _payload_time(payload, 'requested_time'))}"
    )


def _advance_bot(session: Session, conversation: WhatsAppConversation, incoming_text: str | None) -> str | None:
    text = (incoming_text or "").strip()
    normalized = _normalize_text(text)
    payload = _payload_data(conversation)

    if normalized in {"humano", "asesor", "persona"}:
        payload["previous_bot_state"] = conversation.bot_state
        conversation.payload = payload
        conversation.mode = WhatsAppConversationMode.HUMAN.value
        conversation.bot_state = WhatsAppBotState.HUMAN_MODE.value
        return "Te conecto con una persona de nuestro equipo. Quedamos atentos."

    if conversation.mode == WhatsAppConversationMode.HUMAN.value:
        return None

    if conversation.bot_state in {"", None, WhatsAppBotState.NEW.value}:
        conversation.bot_state = WhatsAppBotState.WAITING_NAME.value
        return "Hola, bienvenido a Torqly. Para agendar, comparteme tu nombre completo."

    if conversation.bot_state == WhatsAppBotState.WAITING_NAME.value:
        if len(text) < 2:
            return "Necesito tu nombre para continuar. Como te llamas?"
        payload["customer_name"] = text
        conversation.payload = payload
        conversation.display_name = text
        conversation.bot_state = WhatsAppBotState.WAITING_VEHICLE.value
        return "Perfecto. Que vehiculo deseas agendar? Ejemplo: Honda Civic negro."

    if conversation.bot_state == WhatsAppBotState.WAITING_VEHICLE.value:
        if len(text) < 2:
            return "Compárteme marca y modelo del vehiculo, por favor."
        payload["vehicle_text"] = text
        conversation.payload = payload
        conversation.bot_state = WhatsAppBotState.WAITING_SERVICE.value
        return _service_prompt(session)

    if conversation.bot_state == WhatsAppBotState.WAITING_SERVICE.value:
        matched_service = _match_service(session, text)
        if not matched_service:
            return _service_prompt(session)
        payload["service_text"] = matched_service.name
        payload["matched_service_id"] = matched_service.id
        conversation.payload = payload
        conversation.bot_state = WhatsAppBotState.WAITING_DATE.value
        return "Que fecha prefieres? Usa formato DD/MM/AAAA, YYYY-MM-DD o escribe manana."

    if conversation.bot_state == WhatsAppBotState.WAITING_DATE.value:
        parsed_date = _parse_date_from_text(text)
        if not parsed_date:
            return "No pude leer la fecha. Intenta con DD/MM/AAAA o YYYY-MM-DD."
        payload["requested_date"] = parsed_date.isoformat()
        conversation.payload = payload
        conversation.bot_state = WhatsAppBotState.WAITING_TIME.value
        return "Que hora prefieres? Usa formato HH:MM en horario de 24 horas."

    if conversation.bot_state == WhatsAppBotState.WAITING_TIME.value:
        parsed_time = _parse_time_from_text(text)
        if not parsed_time:
            return "No pude leer la hora. Intenta con formato HH:MM, por ejemplo 16:30."
        payload["requested_time"] = parsed_time.isoformat()
        conversation.payload = payload
        conversation.bot_state = WhatsAppBotState.CONFIRMING.value
        return (
            "Confirma tu cita con este resumen:\n"
            f"{_bot_summary(conversation)}\n"
            "Responde SI para confirmar o NO para cambiar datos."
        )

    if conversation.bot_state == WhatsAppBotState.CONFIRMING.value:
        if normalized in NEGATIVE_WORDS:
            conversation.bot_state = WhatsAppBotState.WAITING_SERVICE.value
            return "De acuerdo. Indica de nuevo el servicio que deseas agendar."
        if normalized not in AFFIRMATIVE_WORDS:
            return "Responde SI para confirmar o NO para corregir la cita."
        appointment = create_appointment_from_conversation(session, conversation.id)
        conversation = get_conversation(session, conversation.id)
        conversation.bot_state = WhatsAppBotState.COMPLETED.value
        _set_payload_value(conversation, last_appointment_id=appointment.id)
        return None

    if conversation.bot_state == WhatsAppBotState.COMPLETED.value:
        if normalized in {"nueva cita", "agendar", "otra cita"}:
            conversation.bot_state = WhatsAppBotState.WAITING_VEHICLE.value
            return "Claro. Que vehiculo deseas agendar ahora?"
        return "Tu conversacion sigue abierta. Si deseas otra cita, escribe 'nueva cita'."

    return None


def _ensure_client_for_conversation(session: Session, conversation: WhatsAppConversation):
    if conversation.client_id:
        client = session.get(Client, conversation.client_id)
        if client and client.deleted_at is None:
            return client

    client = _find_client_by_phone(session, conversation.phone)
    payload = _payload_data(conversation)
    if client:
        conversation.client_id = client.id
        return client

    client = Client(
        name=payload.get("customer_name") or conversation.display_name or conversation.phone,
        phone=conversation.phone,
        email=None,
        address=None,
        notes="Creado automaticamente desde WhatsApp Cloud API.",
        is_active=True,
    )
    session.add(client)
    session.flush()
    conversation.client_id = client.id
    log_action(
        session,
        actor=None,
        action="whatsapp.client.auto_create",
        entity_type="client",
        entity_id=client.id,
        description="Cliente creado automaticamente desde conversacion WhatsApp.",
    )
    return client


def _ensure_vehicle_for_client(session: Session, client: Client, vehicle_text: str | None) -> Vehicle:
    brand, model = _parse_vehicle_label(vehicle_text or "")
    vehicle = session.scalar(
        select(Vehicle)
        .where(Vehicle.client_id == client.id)
        .where(Vehicle.deleted_at.is_(None))
        .where(func.lower(Vehicle.brand) == brand.lower())
        .where(func.lower(Vehicle.model) == model.lower())
    )
    if vehicle:
        return vehicle

    vehicle = Vehicle(
        client_id=client.id,
        brand=brand,
        model=model,
        year=None,
        color=None,
        plates=None,
        notes=f"Creado desde WhatsApp: {vehicle_text or ''}".strip(),
        is_active=True,
    )
    session.add(vehicle)
    session.flush()
    log_action(
        session,
        actor=None,
        action="whatsapp.vehicle.auto_create",
        entity_type="vehicle",
        entity_id=vehicle.id,
        description="Vehiculo creado automaticamente desde conversacion WhatsApp.",
    )
    return vehicle


def create_appointment_from_conversation(
    session: Session,
    conversation_id: int,
    *,
    service_catalog_id: int | None = None,
    scheduled_date: date | None = None,
    scheduled_time: time | None = None,
    operator_id: int | None = None,
    actor=None,
):
    conversation = get_conversation(session, conversation_id)
    payload = _payload_data(conversation)
    matched_service_id = service_catalog_id or payload.get("matched_service_id")
    service = session.get(ServiceCatalog, matched_service_id) if matched_service_id else None
    if not service or service.deleted_at is not None or not service.is_active:
        service = _match_service(session, payload.get("service_text"))
    if not service:
        raise ValidationError("No se pudo determinar un servicio valido para la conversacion.")

    target_date = scheduled_date or _payload_date(payload, "requested_date")
    target_time = scheduled_time or _payload_time(payload, "requested_time")
    if not target_date or not target_time:
        raise ValidationError("La conversacion todavia no tiene fecha y hora suficientes.")

    client = _ensure_client_for_conversation(session, conversation)
    vehicle = _ensure_vehicle_for_client(session, client, payload.get("vehicle_text"))

    from app.schemas.appointment import AppointmentCreate
    from app.services.appointments import create_appointment

    appointment = create_appointment(
        session,
        AppointmentCreate(
            client_id=client.id,
            vehicle_id=vehicle.id,
            service_catalog_id=service.id,
            operator_id=operator_id,
            whatsapp_integration_id=conversation.integration_account_id,
            scheduled_start=combine_local_date_time(target_date, target_time),
            address=None,
            notes=f"Creada desde WhatsApp. Conversacion #{conversation.id}.",
            status=AppointmentStatus.CONFIRMED,
            origin=AppointmentOrigin.WHATSAPP,
            estimated_price=service.base_price,
        ),
        actor=actor,
    )
    conversation.client_id = client.id
    conversation.summary = _bot_summary(conversation)
    conversation.bot_state = WhatsAppBotState.COMPLETED.value
    conversation.status = WhatsAppConversationStatus.OPEN.value
    conversation.last_message_at = local_now()
    _set_payload_value(conversation, last_appointment_id=appointment.id, matched_service_id=service.id)
    return appointment


def set_human_mode(session: Session, conversation_id: int, *, enabled: bool, actor) -> WhatsAppConversation:
    conversation = get_conversation(session, conversation_id)
    payload = _payload_data(conversation)
    if enabled:
        payload["previous_bot_state"] = conversation.bot_state
        conversation.mode = WhatsAppConversationMode.HUMAN.value
        conversation.bot_state = WhatsAppBotState.HUMAN_MODE.value
        conversation.assigned_admin_user_id = actor.id
    else:
        conversation.mode = WhatsAppConversationMode.BOT.value
        conversation.bot_state = payload.get("previous_bot_state") or WhatsAppBotState.WAITING_NAME.value
    conversation.payload = payload
    log_action(
        session,
        actor=actor,
        action="whatsapp.conversation.mode",
        entity_type="conversation",
        entity_id=conversation.id,
        description="Modo humano actualizado.",
        payload={"enabled": enabled},
    )
    session.commit()
    return get_conversation(session, conversation.id)


def link_conversation_client(session: Session, conversation_id: int, *, client_id: int, actor) -> WhatsAppConversation:
    conversation = get_conversation(session, conversation_id)
    client = session.get(Client, client_id)
    if not client or client.deleted_at is not None:
        raise ValidationError("Cliente invalido para relacionar.")
    conversation.client_id = client.id
    log_action(
        session,
        actor=actor,
        action="whatsapp.conversation.link_client",
        entity_type="conversation",
        entity_id=conversation.id,
        description=f"Conversacion relacionada al cliente {client.id}.",
    )
    session.commit()
    return get_conversation(session, conversation.id)


def reply_manually(session: Session, conversation_id: int, *, body: str, actor) -> dict:
    conversation = get_conversation(session, conversation_id)
    if not body.strip():
        raise ValidationError("Escribe un mensaje para responder.")
    delivery = send_conversation_message(session, conversation, body=body.strip(), actor=actor)
    conversation.last_message_at = local_now()
    session.commit()
    return delivery


def send_appointment_confirmation_message(session: Session, appointment) -> dict | None:
    if not appointment.client or not appointment.client.phone:
        return None
    conversation = get_or_create_conversation(
        session,
        phone=appointment.client.phone,
        display_name=appointment.client.name,
        integration_account_id=getattr(appointment, "whatsapp_integration_id", None),
    )
    conversation.client_id = appointment.client.id
    conversation.bot_state = WhatsAppBotState.COMPLETED.value
    delivery = send_appointment_confirmation(session, appointment, appointment.client.phone)
    _store_outbound_message(
        session,
        conversation=conversation,
        body=(
            f"Tu cita esta confirmada para "
            f"{appointment.scheduled_start.astimezone(get_timezone()).strftime('%d/%m/%Y %H:%M')}. "
            f"Servicio: {appointment.service.name if appointment.service else 'Servicio'}."
        ),
        delivery_result=delivery,
    )
    session.commit()
    return delivery


def send_appointment_cancellation_message(session: Session, appointment) -> dict | None:
    if not appointment.client or not appointment.client.phone:
        return None
    conversation = get_or_create_conversation(
        session,
        phone=appointment.client.phone,
        display_name=appointment.client.name,
        integration_account_id=getattr(appointment, "whatsapp_integration_id", None),
    )
    conversation.client_id = appointment.client.id
    delivery = send_appointment_cancellation(session, appointment, appointment.client.phone)
    _store_outbound_message(
        session,
        conversation=conversation,
        body=(
            f"Tu cita de {appointment.service.name if appointment.service else 'servicio'} "
            f"para {appointment.scheduled_start.astimezone(get_timezone()).strftime('%d/%m/%Y %H:%M')} "
            "fue cancelada."
        ),
        delivery_result=delivery,
    )
    session.commit()
    return delivery


def send_service_completed_message(session: Session, appointment) -> dict | None:
    if not appointment.client or not appointment.client.phone:
        return None
    conversation = get_or_create_conversation(
        session,
        phone=appointment.client.phone,
        display_name=appointment.client.name,
        integration_account_id=getattr(appointment, "whatsapp_integration_id", None),
    )
    conversation.client_id = appointment.client.id
    delivery = send_service_completed(session, appointment, appointment.client.phone)
    _store_outbound_message(
        session,
        conversation=conversation,
        body=(
            f"Tu servicio {appointment.service.name if appointment.service else ''} "
            "fue marcado como terminado. Gracias por confiar en Torqly."
        ).strip(),
        delivery_result=delivery,
    )
    session.commit()
    return delivery


def process_whatsapp_webhook(session: Session, payload: dict) -> dict:
    inbound_messages, status_updates = parse_whatsapp_webhook_payload(payload)
    processed_replies = 0
    processed_inbound = 0
    processed_statuses = 0

    for event in inbound_messages:
        account = resolve_whatsapp_account_from_metadata(session, event.get("metadata"))
        conversation = get_or_create_conversation(
            session,
            phone=event["phone"],
            display_name=event.get("display_name"),
            integration_account_id=account.id if account else None,
        )
        _store_inbound_message(session, conversation=conversation, event=event)
        processed_inbound += 1

        reply = _advance_bot(session, conversation, event.get("content"))
        if reply:
            send_conversation_message(
                session,
                conversation,
                body=reply,
                integration_account_id=conversation.integration_account_id,
            )
            processed_replies += 1

    for status_event in status_updates:
        _update_delivery_status(session, status_event)
        processed_statuses += 1

    session.commit()
    return {
        "inbound_messages": processed_inbound,
        "replies": processed_replies,
        "status_updates": processed_statuses,
    }
