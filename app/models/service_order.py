from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class ServiceOrder(Base, TimestampMixin):
    __tablename__ = "service_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    cash_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("cash_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vehicle_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True
    )

    service_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    daily_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discount_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="en_cola")
    payment_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pendiente")
    payment_method: Mapped[str | None] = mapped_column(String(30), nullable=True)

    is_domicilio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    branch: Mapped[str] = mapped_column(String(20), nullable=False, default="local")
    delivery_address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cancelled_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    client = relationship("Client")
    vehicle = relationship("Vehicle")
    cash_session = relationship("CashSession", back_populates="orders")
    items = relationship("ServiceOrderItem", back_populates="order", cascade="all, delete-orphan")
    washers = relationship("ServiceOrderWasher", back_populates="order", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by_id])
    canceller = relationship("User", foreign_keys=[cancelled_by_id])


class ServiceOrderItem(Base, TimestampMixin):
    __tablename__ = "service_order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    catalog_id: Mapped[int | None] = mapped_column(
        ForeignKey("services_catalog.id", ondelete="SET NULL"), nullable=True
    )
    custom_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    order = relationship("ServiceOrder", back_populates="items")
    catalog = relationship("ServiceCatalog")

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


class ServiceOrderWasher(Base, TimestampMixin):
    __tablename__ = "service_order_washers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    order = relationship("ServiceOrder", back_populates="washers")
    user = relationship("User", foreign_keys=[user_id])
    paid_by = relationship("User", foreign_keys=[paid_by_id])
