from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class CatalogFamily(Base, TimestampMixin):
    __tablename__ = "catalog_families"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    branch: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color_code: Mapped[str] = mapped_column(String(7), nullable=False, default="#334155")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    subfamilies = relationship(
        "CatalogSubfamily", back_populates="family", order_by="CatalogSubfamily.sort_order"
    )


class CatalogSubfamily(Base, TimestampMixin):
    __tablename__ = "catalog_subfamilies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("catalog_families.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    family = relationship("CatalogFamily", back_populates="subfamilies")
    services = relationship("ServiceCatalog", back_populates="subfamily")
