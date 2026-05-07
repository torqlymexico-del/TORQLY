from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import ServiceType
from app.models.base import Base
from app.models.mixins import ActorAuditMixin, SoftDeleteMixin, TimestampMixin


class ServiceCatalog(Base, TimestampMixin, SoftDeleteMixin, ActorAuditMixin):
    __tablename__ = "services_catalog"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    subfamily_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_subfamilies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    service_type: Mapped[str] = mapped_column(String(30), nullable=False, default=ServiceType.WASH.value)
    suggested_commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=30)
    color_code: Mapped[str] = mapped_column(String(7), nullable=False, default="#334155")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    subfamily = relationship("CatalogSubfamily", back_populates="services")
    appointments = relationship("Appointment", back_populates="service")
    payment_items = relationship("PaymentItem", back_populates="service")

