from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class TeamMessage(Base, TimestampMixin):
    __tablename__ = "team_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attachment_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
