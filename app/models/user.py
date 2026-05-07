from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import UserRole
from app.models.base import Base
from app.models.mixins import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    active_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(25), nullable=True, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    privacy_policy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    privacy_policy_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default=UserRole.OPERATOR.value)
    clickup_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    weekly_salary: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    commission_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    permissions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company = relationship("Company", back_populates="users", foreign_keys=[company_id])
    active_company = relationship("Company", back_populates="active_users", foreign_keys=[active_company_id])
    appointments_as_operator = relationship(
        "Appointment",
        back_populates="operator",
        foreign_keys="Appointment.operator_id",
    )
    payments_collected = relationship(
        "Payment",
        back_populates="cashier",
        foreign_keys="Payment.cashier_id",
    )
    commissions = relationship("Commission", back_populates="user", foreign_keys="Commission.user_id")
    cash_cuts = relationship("CashCut", back_populates="cashier", foreign_keys="CashCut.cashier_id")
    opened_cash_cuts = relationship(
        "CashCut",
        back_populates="opened_by",
        foreign_keys="CashCut.opened_by_user_id",
    )
    closed_cash_cuts = relationship(
        "CashCut",
        back_populates="closed_by",
        foreign_keys="CashCut.closed_by_user_id",
    )
    notifications = relationship("Notification", back_populates="user", foreign_keys="Notification.user_id")
    internal_bot_messages = relationship(
        "InternalBotMessage",
        back_populates="user",
        foreign_keys="InternalBotMessage.user_id",
    )
    whatsapp_conversations_assigned = relationship(
        "WhatsAppConversation",
        back_populates="assigned_admin",
        foreign_keys="WhatsAppConversation.assigned_admin_user_id",
    )
    created_integration_accounts = relationship(
        "IntegrationAccount",
        back_populates="creator",
        foreign_keys="IntegrationAccount.created_by",
    )
