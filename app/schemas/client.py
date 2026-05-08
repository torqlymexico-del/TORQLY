from pydantic import EmailStr, Field

from app.schemas.common import ORMBaseModel


class ClientBase(ORMBaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=25)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    is_active: bool = True
    branch: str = "local"


class ClientCreate(ClientBase):
    pass


class ClientUpdate(ORMBaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=7, max_length=25)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    is_active: bool | None = None


class ClientRead(ClientBase):
    id: int
    branch: str = "local"

