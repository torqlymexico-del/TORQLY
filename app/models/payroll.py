from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class PayrollSetting(Base, TimestampMixin):
    __tablename__ = "payroll_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"), nullable=True, unique=True, index=True
    )
    rag_unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=20)


class PayrollDeduction(Base, TimestampMixin):
    __tablename__ = "payroll_deductions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    deduction_type: Mapped[str] = mapped_column(String(30), nullable=False, default="trapos")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by_id])


class CommissionPayment(Base, TimestampMixin):
    __tablename__ = "commission_payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_source: Mapped[str] = mapped_column(String(20), nullable=False, default="efectivo")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cash_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("cash_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user = relationship("User", foreign_keys=[user_id])
    paid_by = relationship("User", foreign_keys=[paid_by_id])
    cash_session = relationship("CashSession")


class SalaryPayment(Base, TimestampMixin):
    __tablename__ = "salary_payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_source: Mapped[str] = mapped_column(String(20), nullable=False, default="efectivo")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cash_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("cash_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user = relationship("User", foreign_keys=[user_id])
    paid_by = relationship("User", foreign_keys=[paid_by_id])
    cash_session = relationship("CashSession")
