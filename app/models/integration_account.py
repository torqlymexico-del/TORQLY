from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import IntegrationAccountProvider, IntegrationAccountStatus
from app.models.base import Base
from app.models.mixins import TimestampMixin


class IntegrationAccount(Base, TimestampMixin):
    __tablename__ = "integration_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=IntegrationAccountProvider.CUSTOM.value,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=IntegrationAccountStatus.INACTIVE.value,
        index=True,
    )
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False)
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    company = relationship("Company", back_populates="integration_accounts")
    creator = relationship("User", foreign_keys=[created_by])
    whatsapp_conversations = relationship(
        "WhatsAppConversation",
        back_populates="integration_account",
        foreign_keys="WhatsAppConversation.integration_account_id",
    )
    whatsapp_messages = relationship(
        "WhatsAppMessage",
        back_populates="integration_account",
        foreign_keys="WhatsAppMessage.integration_account_id",
    )
    integration_logs = relationship(
        "IntegrationLog",
        back_populates="integration_account",
        foreign_keys="IntegrationLog.integration_account_id",
    )
