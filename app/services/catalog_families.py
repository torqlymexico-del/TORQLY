from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CatalogFamily, CatalogSubfamily
from app.services.exceptions import NotFoundError


def list_families(session: Session) -> list[CatalogFamily]:
    return list(
        session.scalars(
            select(CatalogFamily)
            .where(CatalogFamily.is_active.is_(True))
            .order_by(CatalogFamily.sort_order, CatalogFamily.name)
        ).all()
    )


def get_family(session: Session, family_id: int) -> CatalogFamily:
    f = session.get(CatalogFamily, family_id)
    if not f:
        raise NotFoundError("Familia no encontrada.")
    return f


def create_family(session: Session, *, name: str, color_code: str = "#334155", sort_order: int = 0) -> CatalogFamily:
    f = CatalogFamily(name=name, color_code=color_code, sort_order=sort_order)
    session.add(f)
    session.commit()
    session.refresh(f)
    return f


def update_family(
    session: Session, family_id: int, *, name: str | None = None, color_code: str | None = None,
    sort_order: int | None = None, is_active: bool | None = None
) -> CatalogFamily:
    f = get_family(session, family_id)
    if name is not None:
        f.name = name
    if color_code is not None:
        f.color_code = color_code
    if sort_order is not None:
        f.sort_order = sort_order
    if is_active is not None:
        f.is_active = is_active
    session.commit()
    session.refresh(f)
    return f


def list_subfamilies(session: Session, family_id: int | None = None) -> list[CatalogSubfamily]:
    q = select(CatalogSubfamily).where(CatalogSubfamily.is_active.is_(True))
    if family_id is not None:
        q = q.where(CatalogSubfamily.family_id == family_id)
    return list(session.scalars(q.order_by(CatalogSubfamily.sort_order, CatalogSubfamily.name)).all())


def get_subfamily(session: Session, subfamily_id: int) -> CatalogSubfamily:
    sf = session.get(CatalogSubfamily, subfamily_id)
    if not sf:
        raise NotFoundError("Subfamilia no encontrada.")
    return sf


def create_subfamily(
    session: Session, *, family_id: int, name: str, sort_order: int = 0
) -> CatalogSubfamily:
    sf = CatalogSubfamily(family_id=family_id, name=name, sort_order=sort_order)
    session.add(sf)
    session.commit()
    session.refresh(sf)
    return sf


def update_subfamily(
    session: Session, subfamily_id: int, *, name: str | None = None,
    sort_order: int | None = None, is_active: bool | None = None
) -> CatalogSubfamily:
    sf = get_subfamily(session, subfamily_id)
    if name is not None:
        sf.name = name
    if sort_order is not None:
        sf.sort_order = sort_order
    if is_active is not None:
        sf.is_active = is_active
    session.commit()
    session.refresh(sf)
    return sf
