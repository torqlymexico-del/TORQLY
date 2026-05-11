from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import AppointmentOrigin, AppointmentStatus, ChargeStatus, JobStatus
from app.models.base import Base
from app.models.mixins import ActorAuditMixin, SoftDeleteMixin, TimestampMixin


class Appointment(Base, TimestampMixin, SoftDeleteMixin, ActorAuditMixin):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    service_catalog_id: Mapped[int] = mapped_column(ForeignKey("services_catalog.id"), nullable=False, index=True)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=AppointmentStatus.PENDING.value)
    origin: Mapped[str] = mapped_column(String(30), nullable=False, default=AppointmentOrigin.MANUAL.value)
    charge_status: Mapped[str] = mapped_column(String(30), nullable=False, default=ChargeStatus.PENDING.value)
    estimated_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    google_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clickup_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clickup_task_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_integration_id: Mapped[int | None] = mapped_column(
        ForeignKey("integration_accounts.id"),
        nullable=True,
        index=True,
    )
    google_calendar_integration_id: Mapped[int | None] = mapped_column(
        ForeignKey("integration_accounts.id"),
        nullable=True,
        index=True,
    )
    google_sheets_integration_id: Mapped[int | None] = mapped_column(
        ForeignKey("integration_accounts.id"),
        nullable=True,
        index=True,
    )
    clickup_integration_id: Mapped[int | None] = mapped_column(
        ForeignKey("integration_accounts.id"),
        nullable=True,
        index=True,
    )
    meta_business_integration_id: Mapped[int | None] = mapped_column(
        ForeignKey("integration_accounts.id"),
        nullable=True,
        index=True,
    )
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operator_reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_for_charge_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    client = relationship("Client", back_populates="appointments")
    vehicle = relationship("Vehicle", back_populates="appointments")
    service = relationship("ServiceCatalog", back_populates="appointments")
    operator = relationship("User", back_populates="appointments_as_operator", foreign_keys=[operator_id])
    whatsapp_integration = relationship("IntegrationAccount", foreign_keys=[whatsapp_integration_id])
    google_calendar_integration = relationship("IntegrationAccount", foreign_keys=[google_calendar_integration_id])
    google_sheets_integration = relationship("IntegrationAccount", foreign_keys=[google_sheets_integration_id])
    clickup_integration = relationship("IntegrationAccount", foreign_keys=[clickup_integration_id])
    meta_business_integration = relationship("IntegrationAccount", foreign_keys=[meta_business_integration_id])
    service_job = relationship("ServiceJob", back_populates="appointment", uselist=False)
    payments = relationship("Payment", back_populates="appointment")
    notifications = relationship("Notification", back_populates="appointment")


class ServiceJob(Base, TimestampMixin):
    __tablename__ = "service_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), nullable=False, unique=True, index=True)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_duration_minutes: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=JobStatus.PENDING.value)
    started_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    completed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    appointment = relationship("Appointment", back_populates="service_job")
    operator = relationship("User", foreign_keys=[operator_id])
    commissions = relationship("Commission", back_populates="service_job")
    inventory_movements = relationship("InventoryMovement", back_populates="service_job")
