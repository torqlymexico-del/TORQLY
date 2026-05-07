from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import UserRole
from app.models import User
from app.security import get_password_hash
from app.services.companies import ensure_default_company


def ensure_default_admin(session: Session) -> User | None:
    company = ensure_default_company(session)
    if not settings.bootstrap_admin_on_startup:
        return None

    existing_admin = session.scalar(select(User).where(User.phone == settings.default_admin_phone))
    if existing_admin:
        if not existing_admin.company_id:
            existing_admin.company_id = company.id
        if not existing_admin.active_company_id:
            existing_admin.active_company_id = existing_admin.company_id
        session.commit()
        return existing_admin

    admin = User(
        company_id=company.id,
        active_company_id=company.id,
        name=settings.default_admin_name,
        phone=settings.default_admin_phone,
        email=settings.default_admin_email,
        password_hash=get_password_hash(settings.default_admin_password),
        role=UserRole.ADMIN.value,
        permissions={"can_select_integrations": True},
        weekly_salary=0,
        commission_percentage=0,
        is_active=True,
        notes="Usuario bootstrap creado automaticamente al iniciar.",
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin
