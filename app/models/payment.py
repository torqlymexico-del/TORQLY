from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import PaymentItemType, PaymentMethod
from app.models.base import Base
from app.models.mixins import ActorAuditMixin, TimestampMixin


class Payment(Base, TimestampMixin, ActorAuditMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), nullable=True, index=True)
    cashier_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    ticket_number: Mapped[str | None] = mapped_column(String(40), nullable=True, unique=True, index=True)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    extras_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False, default=PaymentMethod.CASH.value)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    appointment = relationship("Appointment", back_populates="payments")
    client = relationship("Client")
    cashier = relationship("User", back_populates="payments_collected", foreign_keys=[cashier_id])
    items = relationship("PaymentItem", back_populates="payment", cascade="all, delete-orphan")
    commissions = relationship("Commission", back_populates="payment")


class PaymentItem(Base, TimestampMixin):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    service_catalog_id: Mapped[int | None] = mapped_column(ForeignKey("services_catalog.id"), nullable=True)
    item_type: Mapped[str] = mapped_column(String(30), nullable=False, default=PaymentItemType.SERVICE.value)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    apply_commission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    payment = relationship("Payment", back_populates="items")
    service = relationship("ServiceCatalog", back_populates="payment_items")
