from datetime import date
from decimal import Decimal

from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import CashCutStatus
from app.models.base import Base
from app.models.mixins import TimestampMixin


class CashCut(Base, TimestampMixin):
    __tablename__ = "cash_cuts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cut_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cashier_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    opened_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    closed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_sales: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    cash_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    card_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    transfer_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    courtesy_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discounts_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    commissions_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    cost_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    estimated_profit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    services_completed: Mapped[int] = mapped_column(nullable=False, default=0)
    services_charged: Mapped[int] = mapped_column(nullable=False, default=0)
    services_canceled: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=CashCutStatus.OPEN.value)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    cashier = relationship("User", back_populates="cash_cuts", foreign_keys=[cashier_id])
    opened_by = relationship("User", back_populates="opened_cash_cuts", foreign_keys=[opened_by_user_id])
    closed_by = relationship("User", back_populates="closed_cash_cuts", foreign_keys=[closed_by_user_id])
