from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import (
    MessageDirection,
    WhatsAppBotState,
    WhatsAppConversationMode,
    WhatsAppConversationStatus,
)
from app.models.base import Base
from app.models.mixins import TimestampMixin


class WhatsAppConversation(Base, TimestampMixin):
    __tablename__ = "whatsapp_conversations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), nullable=True, index=True)
    integration_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("integration_accounts.id"),
        nullable=True,
        index=True,
    )
    phone: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mode: Mapped[str] = mapped_column(String(30), nullable=False, default=WhatsAppConversationMode.BOT.value)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=WhatsAppConversationStatus.OPEN.value)
    bot_state: Mapped[str] = mapped_column(String(30), nullable=False, default=WhatsAppBotState.NEW.value)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    client = relationship("Client", back_populates="whatsapp_conversations")
    integration_account = relationship(
        "IntegrationAccount",
        back_populates="whatsapp_conversations",
        foreign_keys=[integration_account_id],
    )
    messages = relationship("WhatsAppMessage", back_populates="conversation", cascade="all, delete-orphan")
    assigned_admin = relationship(
        "User",
        back_populates="whatsapp_conversations_assigned",
        foreign_keys=[assigned_admin_user_id],
    )


class WhatsAppMessage(Base, TimestampMixin):
    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("whatsapp_conversations.id"), nullable=False, index=True)
    integration_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("integration_accounts.id"),
        nullable=True,
        index=True,
    )
    direction: Mapped[str] = mapped_column(String(30), nullable=False, default=MessageDirection.INBOUND.value)
    message_type: Mapped[str] = mapped_column(String(30), nullable=False, default="text")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation = relationship("WhatsAppConversation", back_populates="messages")
    integration_account = relationship(
        "IntegrationAccount",
        back_populates="whatsapp_messages",
        foreign_keys=[integration_account_id],
    )
