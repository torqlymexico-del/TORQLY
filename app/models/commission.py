from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class Commission(Base, TimestampMixin):
    __tablename__ = "commissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True, index=True)
    service_job_id: Mapped[int | None] = mapped_column(ForeignKey("service_jobs.id"), nullable=True, index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True, index=True)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    extra_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    calculation_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    user = relationship("User", back_populates="commissions", foreign_keys=[user_id])
    service_job = relationship("ServiceJob", back_populates="commissions")
    payment = relationship("Payment", back_populates="commissions")
