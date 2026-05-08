from datetime import datetime

from app.schemas.common import ORMBaseModel


class InviteCodeCreate(ORMBaseModel):
    role: str
    label: str | None = None


class InviteCodeRead(ORMBaseModel):
    id: int
    code: str
    role: str
    label: str | None
    is_active: bool
    created_by_name: str | None = None
    used_by_name: str | None = None
    used_at: datetime | None
    created_at: datetime
