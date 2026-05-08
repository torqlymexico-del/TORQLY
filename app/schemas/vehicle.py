from typing import Literal

from pydantic import Field

from app.schemas.common import ORMBaseModel

VehicleType = Literal["sedan", "suv", "camioneta", "van", "moto", "otro"]


class VehicleBase(ORMBaseModel):
    client_id: int | None = None
    branch: str = Field(default="local", max_length=20)
    brand: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    type: VehicleType | None = "sedan"
    year: int | None = Field(default=None, ge=1950, le=2100)
    color: str | None = Field(default=None, max_length=50)
    plates: str | None = Field(default=None, max_length=20)
    notes: str | None = None
    is_active: bool = True


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(ORMBaseModel):
    client_id: int | None = None
    brand: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    type: VehicleType | None = None
    year: int | None = Field(default=None, ge=1950, le=2100)
    color: str | None = Field(default=None, max_length=50)
    plates: str | None = Field(default=None, max_length=20)
    notes: str | None = None
    is_active: bool | None = None


class VehicleRead(VehicleBase):
    id: int

