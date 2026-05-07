from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.enums import AppointmentOrigin, AppointmentStatus
from app.schemas.common import ORMBaseModel


class AppointmentBase(ORMBaseModel):
    client_id: int
    vehicle_id: int
    service_catalog_id: int
    operator_id: int | None = None
    whatsapp_integration_id: int | None = None
    google_calendar_integration_id: int | None = None
    google_sheets_integration_id: int | None = None
    clickup_integration_id: int | None = None
    meta_business_integration_id: int | None = None
    scheduled_start: datetime
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    status: AppointmentStatus = AppointmentStatus.PENDING
    origin: AppointmentOrigin = AppointmentOrigin.MANUAL
    estimated_price: Decimal | None = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(ORMBaseModel):
    client_id: int | None = None
    vehicle_id: int | None = None
    service_catalog_id: int | None = None
    operator_id: int | None = None
    whatsapp_integration_id: int | None = None
    google_calendar_integration_id: int | None = None
    google_sheets_integration_id: int | None = None
    clickup_integration_id: int | None = None
    meta_business_integration_id: int | None = None
    scheduled_start: datetime | None = None
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    status: AppointmentStatus | None = None
    origin: AppointmentOrigin | None = None
    estimated_price: Decimal | None = None
    cancellation_reason: str | None = Field(default=None, max_length=255)


class AppointmentRead(AppointmentBase):
    id: int
    charge_status: str = "pendiente"
    paid_at: datetime | None = None
    google_event_id: str | None = None
    clickup_task_id: str | None = None
    clickup_task_url: str | None = None
    whatsapp_integration_id: int | None = None
    google_calendar_integration_id: int | None = None
    google_sheets_integration_id: int | None = None
    clickup_integration_id: int | None = None
    meta_business_integration_id: int | None = None
    client_name: str | None = None
    vehicle_label: str | None = None
    service_name: str | None = None
    operator_name: str | None = None
