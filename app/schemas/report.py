from datetime import date
from decimal import Decimal

from app.schemas.common import ORMBaseModel


class BasicSummaryRead(ORMBaseModel):
    target_date: date
    total_sales: Decimal
    cash_total: Decimal
    card_total: Decimal
    transfer_total: Decimal
    courtesy_total: Decimal
    discounts_total: Decimal
    commissions_total: Decimal
    cost_total: Decimal
    estimated_profit: Decimal
    services_charged: int
    services_canceled: int
    pending_charges: int
