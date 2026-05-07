from __future__ import annotations

import base64
import json

from app.config import settings


SENSITIVE_KEYWORDS = (
    "token",
    "secret",
    "password",
    "authorization",
    "credentials",
    "cookie",
)


def _get_fernet():
    master_key = settings.credential_master_key
    if not master_key:
        raise ValueError("CREDENTIAL_MASTER_KEY no configurada.")
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ValueError("La dependencia cryptography no esta disponible.") from exc
    try:
        return Fernet(master_key.encode("utf-8"))
    except Exception as exc:  # pragma: no cover - invalid key guard
        raise ValueError("CREDENTIAL_MASTER_KEY no tiene un formato valido.") from exc


def encrypt_credentials(payload: dict | None) -> str | None:
    if not payload:
        return None
    fernet = _get_fernet()
    raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return fernet.encrypt(raw).decode("utf-8")


def decrypt_credentials(payload: str | None) -> dict:
    if not payload:
        return {}
    fernet = _get_fernet()
    raw = fernet.decrypt(payload.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))


def _mask_string(value: str | None) -> str | None:
    if value is None:
        return None
    clean = str(value)
    if len(clean) <= 4:
        return "*" * len(clean)
    return f"{'*' * max(len(clean) - 4, 4)}{clean[-4:]}"


def mask_sensitive_payload(payload: dict | list | str | None):
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if any(token in key.lower() for token in SENSITIVE_KEYWORDS):
                sanitized[key] = _mask_string(str(value)) if value is not None else None
            else:
                sanitized[key] = mask_sensitive_payload(value)
        return sanitized
    if isinstance(payload, list):
        return [mask_sensitive_payload(item) for item in payload]
    return payload


def credential_suffix(payload: dict, *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value:
            return str(value)[-4:]
    return None


def generate_master_key() -> str:
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ValueError("La dependencia cryptography no esta disponible.") from exc
    return Fernet.generate_key().decode("utf-8")
