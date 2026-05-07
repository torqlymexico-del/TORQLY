from decimal import Decimal

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import InventoryMovementType
from app.models.base import Base
from app.models.mixins import ActorAuditMixin, SoftDeleteMixin, TimestampMixin


class InventoryProduct(Base, TimestampMixin, SoftDeleteMixin, ActorAuditMixin):
    __tablename__ = "inventory_products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    stock: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(30), nullable=False, default="pieza")
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    low_stock_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    movements = relationship("InventoryMovement", back_populates="product")


class InventoryMovement(Base, TimestampMixin, ActorAuditMixin):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("inventory_products.id"), nullable=False, index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True, index=True)
    service_job_id: Mapped[int | None] = mapped_column(ForeignKey("service_jobs.id"), nullable=True, index=True)
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False, default=InventoryMovementType.CONSUMPTION.value)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product = relationship("InventoryProduct", back_populates="movements")
    service_job = relationship("ServiceJob", back_populates="inventory_movements")
