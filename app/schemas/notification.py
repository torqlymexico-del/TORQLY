from datetime import datetime

from app.schemas.common import ORMBaseModel


class NotificationRead(ORMBaseModel):
    id: int
    title: str
    message: str
    type: str
    user_id: int | None = None
    appointment_id: int | None = None
    is_read: bool
    created_at: datetime
