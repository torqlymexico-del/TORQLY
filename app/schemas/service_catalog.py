from decimal import Decimal

from pydantic import Field

from app.enums import ServiceType
from app.schemas.common import ORMBaseModel


class ServiceCatalogBase(ORMBaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    base_price: Decimal = Decimal("0.00")
    estimated_duration_minutes: int = Field(default=60, ge=15, le=1440)
    service_type: ServiceType
    is_active: bool = True
    subfamily_id: int | None = None


class ServiceCatalogCreate(ServiceCatalogBase):
    pass


class ServiceCatalogUpdate(ORMBaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    base_price: Decimal | None = None
    estimated_duration_minutes: int | None = Field(default=None, ge=15, le=1440)
    service_type: ServiceType | None = None
    is_active: bool | None = None
    subfamily_id: int | None = None


class ServiceCatalogRead(ServiceCatalogBase):
    id: int

