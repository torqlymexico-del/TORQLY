from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class CashSession(Base, TimestampMixin):
    __tablename__ = "cash_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)

    opened_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    opening_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    closed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closing_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    expected_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    difference_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    total_sales_cash: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_sales_card: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_sales_transfer: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_sales_credit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_sales_courtesy: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_sales_deposit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    courtesy_count: Mapped[int] = mapped_column(nullable=False, default=0)
    change_given: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_sales: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_expenses: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="abierta")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    opener = relationship("User", foreign_keys=[opened_by_id])
    closer = relationship("User", foreign_keys=[closed_by_id])
    movements = relationship("CashMovement", back_populates="session", cascade="all, delete-orphan")
    orders = relationship("ServiceOrder", back_populates="cash_session")


class CashMovement(Base, TimestampMixin):
    __tablename__ = "cash_movements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("cash_sessions.id"), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_void: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("service_orders.id", ondelete="SET NULL"), nullable=True)

    session = relationship("CashSession", back_populates="movements")
    creator = relationship("User", foreign_keys=[created_by_id])
    voider = relationship("User", foreign_keys=[voided_by_id])
