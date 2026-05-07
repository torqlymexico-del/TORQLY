from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class BotCommandRequest(ORMBaseModel):
    command: str = Field(min_length=2)


class BotMessageRead(ORMBaseModel):
    id: int
    command: str
    response: str
    intent: str
    status: str
    created_at: datetime
