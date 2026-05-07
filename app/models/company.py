from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import CompanyStatus
from app.models.base import Base
from app.models.mixins import TimestampMixin


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=CompanyStatus.ACTIVE.value)

    users = relationship("User", back_populates="company", foreign_keys="User.company_id")
    active_users = relationship("User", back_populates="active_company", foreign_keys="User.active_company_id")
    integration_accounts = relationship("IntegrationAccount", back_populates="company")
