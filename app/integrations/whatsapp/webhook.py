import hashlib
import hmac

from app.config import settings


def verify_meta_token(token: str) -> bool:
    return bool(settings.meta_whatsapp_verify_token and token == settings.meta_whatsapp_verify_token)


def verify_meta_signature(body: bytes, signature_header: str | None) -> bool:
    secret = settings.meta_whatsapp_webhook_secret
    if not secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    received = signature_header.split("=", 1)[1].strip()
    return hmac.compare_digest(expected, received)


def parse_whatsapp_webhook_payload(payload: dict) -> tuple[list[dict], list[dict]]:
    inbound_messages: list[dict] = []
    status_updates: list[dict] = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = dict(value.get("metadata", {}) or {})
            if entry.get("id") and not metadata.get("business_account_id"):
                metadata["business_account_id"] = entry.get("id")
            contacts_by_wa_id = {
                contact.get("wa_id"): contact.get("profile", {}).get("name")
                for contact in value.get("contacts", [])
                if contact.get("wa_id")
            }
            for item in value.get("messages", []):
                sender_phone = item.get("from")
                if not sender_phone:
                    continue
                message_type = item.get("type", "text")
                text_body = None
                if message_type == "text":
                    text_body = item.get("text", {}).get("body")
                elif message_type == "button":
                    text_body = item.get("button", {}).get("text")
                elif message_type == "interactive":
                    interactive = item.get("interactive", {})
                    text_body = (
                        interactive.get("button_reply", {}).get("title")
                        or interactive.get("list_reply", {}).get("title")
                    )
                inbound_messages.append(
                    {
                        "phone": sender_phone,
                        "display_name": contacts_by_wa_id.get(sender_phone),
                        "external_message_id": item.get("id"),
                        "message_type": message_type,
                        "content": text_body,
                        "timestamp": item.get("timestamp"),
                        "payload": item,
                        "metadata": metadata,
                    }
                )
            for status in value.get("statuses", []):
                status_updates.append(
                    {
                        "external_message_id": status.get("id"),
                        "status": status.get("status"),
                        "timestamp": status.get("timestamp"),
                        "recipient_id": status.get("recipient_id"),
                        "payload": status,
                        "metadata": metadata,
                    }
                )

    return inbound_messages, status_updates
