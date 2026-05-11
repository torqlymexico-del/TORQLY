from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import ActorAuditMixin, SoftDeleteMixin, TimestampMixin


VEHICLE_TYPES = ("sedan", "suv", "camioneta", "van", "moto", "otro")


class Vehicle(Base, TimestampMixin, SoftDeleteMixin, ActorAuditMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), nullable=True, index=True)
    branch: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    type: Mapped[str | None] = mapped_column(String(20), nullable=True, default="sedan")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    plates: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    client = relationship(
        "Client",
        primaryjoin="Vehicle.client_id == Client.id",
        foreign_keys="[Vehicle.client_id]",
        back_populates="vehicles",
    )
    appointments = relationship("Appointment", back_populates="vehicle")

