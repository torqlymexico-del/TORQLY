from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import ORMBaseModel


class CashCutCreate(ORMBaseModel):
    cut_date: date
    close_cut: bool = False
    notes: str | None = None


class CashCutRead(ORMBaseModel):
    id: int
    cut_date: date
    cashier_id: int | None = None
    opened_by_user_id: int | None = None
    closed_by_user_id: int | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    total_sales: Decimal
    cash_total: Decimal
    card_total: Decimal
    transfer_total: Decimal
    courtesy_total: Decimal
    discounts_total: Decimal
    commissions_total: Decimal
    cost_total: Decimal
    estimated_profit: Decimal
    services_completed: int
    services_charged: int
    services_canceled: int
    status: str
    notes: str | None = None
    opened_by_name: str | None = None
    closed_by_name: str | None = None

