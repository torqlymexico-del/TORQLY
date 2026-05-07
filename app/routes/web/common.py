from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.enums import (
    AppointmentOrigin,
    AppointmentStatus,
    NotificationType,
    PaymentMethod,
    ServiceType,
    UserRole,
)


templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))


def base_context(request: Request, *, current_user=None, **extra) -> dict:
    context = {
        "request": request,
        "current_user": current_user,
        "settings": settings,
        "warnings": settings.integration_warnings(),
        "user_roles": [role.value for role in UserRole],
        "service_types": [item.value for item in ServiceType],
        "appointment_statuses": [item.value for item in AppointmentStatus],
        "appointment_origins": [item.value for item in AppointmentOrigin],
        "payment_methods": [item.value for item in PaymentMethod],
        "notification_types": [item.value for item in NotificationType],
    }
    context.update(extra)
    return context


def redirect_with_message(path: str, message: str | None = None, level: str = "success") -> RedirectResponse:
    destination = path
    if message:
        parsed = urlsplit(path)
        query = dict(parse_qsl(parsed.query))
        query.update({"message": message, "level": level})
        destination = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
    return RedirectResponse(destination, status_code=303)
