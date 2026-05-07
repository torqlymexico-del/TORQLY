from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import CompanyStatus
from app.models import Company, User
from app.services.audit import log_action
from app.services.exceptions import ConflictError, NotFoundError


def slugify_company_name(value: str) -> str:
    return "-".join((value or "").lower().strip().split()) or "empresa-principal"


def list_companies(session: Session) -> list[Company]:
    return list(session.scalars(select(Company).order_by(Company.name.asc())).all())


def get_company(session: Session, company_id: int) -> Company:
    company = session.get(Company, company_id)
    if not company:
        raise NotFoundError("Empresa no encontrada.")
    return company


def ensure_default_company(session: Session) -> Company:
    existing = session.scalar(select(Company).order_by(Company.id.asc()))
    if existing:
        return existing
    company = Company(name="Empresa principal", slug="empresa-principal", status=CompanyStatus.ACTIVE.value)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def create_company(session: Session, *, name: str, actor: User | None = None) -> Company:
    slug = slugify_company_name(name)
    existing = session.scalar(
        select(Company).where((Company.name == name) | (Company.slug == slug))
    )
    if existing:
        raise ConflictError("Ya existe una empresa con ese nombre o slug.")
    company = Company(name=name.strip(), slug=slug, status=CompanyStatus.ACTIVE.value)
    session.add(company)
    session.flush()
    log_action(
        session,
        actor=actor,
        action="companies.create",
        entity_type="company",
        entity_id=company.id,
        description=f"Empresa {company.name} creada.",
    )
    session.commit()
    session.refresh(company)
    return company
