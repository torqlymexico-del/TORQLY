from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.notification import NotificationRead
from app.services.notifications import list_notifications, mark_notification_read
from app.services.exceptions import ServiceError
from app.routes.api.common import raise_api_error


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationRead])
def get_notifications(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
    unread_only: bool = Query(default=False),
    type: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[NotificationRead]:
    items = list_notifications(
        db,
        user=current_user,
        unread_only=unread_only,
        type=type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return [NotificationRead.model_validate(n) for n in items]


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> NotificationRead:
    try:
        n = mark_notification_read(db, notification_id, actor=current_user)
        return NotificationRead.model_validate(n)
    except ServiceError as exc:
        raise_api_error(exc)
