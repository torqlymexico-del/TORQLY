from datetime import date, datetime
from decimal import Decimal

from app.schemas.common import ORMBaseModel


class CommissionRead(ORMBaseModel):
    id: int
    user_id: int
    appointment_id: int | None = None
    service_job_id: int | None = None
    payment_id: int | None = None
    base_amount: Decimal
    extra_amount: Decimal
    total_amount: Decimal
    calculation_note: str | None = None
    calculated_at: datetime | None = None
    period_date: date | None = None
    user_name: str | None = None


class CommissionOperatorSummary(ORMBaseModel):
    operator_id: int
    operator_name: str
    period_label: str
    commission_count: int
    base_amount: Decimal
    extra_amount: Decimal
    total_amount: Decimal

