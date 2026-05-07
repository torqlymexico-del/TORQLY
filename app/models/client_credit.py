from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class ClientCreditAccount(Base, TimestampMixin):
    __tablename__ = "client_credit_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    client = relationship("Client")
    movements = relationship(
        "ClientCreditMovement", back_populates="account", cascade="all, delete-orphan"
    )


class ClientCreditMovement(Base, TimestampMixin):
    __tablename__ = "client_credit_movements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("client_credit_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    account = relationship("ClientCreditAccount", back_populates="movements")
    client = relationship("Client")
    order = relationship("ServiceOrder")
    creator = relationship("User", foreign_keys=[created_by_id])
