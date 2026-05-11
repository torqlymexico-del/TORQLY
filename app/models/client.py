from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import ActorAuditMixin, SoftDeleteMixin, TimestampMixin


class Client(Base, TimestampMixin, SoftDeleteMixin, ActorAuditMixin):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    branch: Mapped[str] = mapped_column(String(20), nullable=False, default="local")
    default_vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    default_service_id: Mapped[int | None] = mapped_column(ForeignKey("services_catalog.id"), nullable=True)

    # All vehicles that belong to this client (via Vehicle.client_id)
    vehicles = relationship(
        "Vehicle",
        primaryjoin="Vehicle.client_id == Client.id",
        foreign_keys="[Vehicle.client_id]",
        back_populates="client",
    )
    appointments = relationship("Appointment", back_populates="client")
    whatsapp_conversations = relationship("WhatsAppConversation", back_populates="client")

    # The client's preferred vehicle for quick re-booking
    default_vehicle = relationship(
        "Vehicle",
        primaryjoin="Client.default_vehicle_id == Vehicle.id",
        foreign_keys="[Client.default_vehicle_id]",
    )
    default_service = relationship(
        "ServiceCatalog",
        primaryjoin="Client.default_service_id == ServiceCatalog.id",
        foreign_keys="[Client.default_service_id]",
    )
