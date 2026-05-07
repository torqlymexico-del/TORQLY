from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.enums import PaymentItemType, PaymentMethod
from app.schemas.common import ORMBaseModel


class PaymentExtraCreate(ORMBaseModel):
    description: str = Field(min_length=1, max_length=255)
    quantity: Decimal = Decimal("1.00")
    unit_price: Decimal = Decimal("0.00")
    apply_commission: bool = True


class PaymentCreate(ORMBaseModel):
    appointment_id: int
    payment_method: PaymentMethod
    discount_total: Decimal = Decimal("0.00")
    notes: str | None = None
    reference: str | None = Field(default=None, max_length=120)
    paid_at: datetime | None = None
    extras: list[PaymentExtraCreate] = []


class PaymentItemRead(ORMBaseModel):
    id: int
    item_type: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    apply_commission: bool


class PaymentRead(ORMBaseModel):
    id: int
    appointment_id: int | None = None
    client_id: int | None = None
    cashier_id: int | None = None
    ticket_number: str | None = None
    reference: str | None = None
    subtotal: Decimal
    extras_total: Decimal
    discount_total: Decimal
    total: Decimal
    payment_method: PaymentMethod
    notes: str | None = None
    paid_at: datetime
    items: list[PaymentItemRead] = []
    client_name: str | None = None
    vehicle_label: str | None = None
    service_name: str | None = None
    operator_name: str | None = None
    cashier_name: str | None = None


class PendingChargeAppointmentRead(ORMBaseModel):
    id: int
    scheduled_start: datetime
    status: str
    charge_status: str
    estimated_price: Decimal
    client_name: str | None = None
    vehicle_label: str | None = None
    service_name: str | None = None
    operator_name: str | None = None

