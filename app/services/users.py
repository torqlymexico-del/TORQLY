from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.enums import UserRole
from app.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.security import get_password_hash, verify_password
from app.services.audit import log_action
from app.services.companies import ensure_default_company
from app.services.exceptions import ConflictError, NotFoundError, ValidationError


def list_users(session: Session, *, company_id: int | None = None, branch: str | None = None) -> list[User]:
    query = select(User).order_by(User.name)
    if company_id is not None:
        query = query.where(User.company_id == company_id)
    if branch is not None:
        query = query.where(User.branch == branch)
    return list(session.scalars(query).all())


def list_assignable_operators(session: Session, *, company_id: int | None = None) -> list[User]:
    query = (
        select(User)
        .where(User.is_active.is_(True))
        .where(User.role.in_(["operator", "supervisor"]))
        .order_by(User.name)
    )
    if company_id is not None:
        query = query.where(User.company_id == company_id)
    return list(session.scalars(query).all())


def get_user(session: Session, user_id: int, *, company_id: int | None = None) -> User:
    query = select(User).where(User.id == user_id)
    if company_id is not None:
        query = query.where(User.company_id == company_id)
    user = session.scalar(query)
    if not user:
        raise NotFoundError("Usuario no encontrado.")
    return user


def authenticate_user(session: Session, *, phone: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.phone == phone))
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    _post_login(session, user)
    return user


def find_google_user(
    session: Session,
    *,
    google_sub: str,
    email: str | None,
) -> "User | None":
    user = session.scalar(select(User).where(User.google_sub == google_sub))
    if user:
        return user
    if email:
        user = session.scalar(select(User).where(User.email == email))
        if user:
            user.google_sub = google_sub
            session.commit()
            session.refresh(user)
            return user
    return None


def create_google_user_from_invite(
    session: Session,
    *,
    google_sub: str,
    email: str | None,
    name: str,
    invite_code: str,
) -> User:
    from app.models import InviteCode

    invite = session.scalar(
        select(InviteCode).where(InviteCode.code == invite_code.upper().strip())
    )
    if not invite:
        raise ValidationError("Código de acceso inválido.")
    if not invite.is_active or invite.used_at is not None:
        raise ValidationError("Este código ya fue utilizado o fue revocado.")

    user = User(
        company_id=invite.company_id,
        active_company_id=invite.company_id,
        name=name or "Usuario Google",
        phone=None,
        email=email,
        password_hash=None,
        google_sub=google_sub,
        role=invite.role,
        branch=invite.branch,
        is_active=True,
    )
    session.add(user)
    session.flush()

    invite.used_by_id = user.id
    invite.used_at = datetime.now(timezone.utc)
    invite.is_active = False

    log_action(
        session,
        actor=user,
        action="users.google_register",
        entity_type="user",
        entity_id=user.id,
        description=f"Registro vía Google con código de acceso: {email or google_sub}.",
    )
    _post_login(session, user)
    return user


def get_or_create_google_user(
    session: Session,
    *,
    google_sub: str,
    email: str | None,
    name: str,
) -> User:
    user = session.scalar(select(User).where(User.google_sub == google_sub))
    if user:
        _post_login(session, user)
        return user

    if email:
        user = session.scalar(select(User).where(User.email == email))
        if user:
            user.google_sub = google_sub
            _post_login(session, user)
            return user

    company = ensure_default_company(session)
    user = User(
        company_id=company.id,
        active_company_id=company.id,
        name=name or "Usuario Google",
        phone=None,
        email=email,
        password_hash=None,
        google_sub=google_sub,
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    session.add(user)
    session.flush()
    log_action(
        session,
        actor=user,
        action="users.google_register",
        entity_type="user",
        entity_id=user.id,
        description=f"Registro via Google: {email or google_sub}.",
    )
    _post_login(session, user)
    return user


def accept_privacy_policy(session: Session, user: User, *, version: str) -> User:
    user.privacy_policy_accepted_at = datetime.now(timezone.utc)
    user.privacy_policy_version = version
    session.commit()
    session.refresh(user)
    return user


def _post_login(session: Session, user: User) -> None:
    user.last_login_at = datetime.now(timezone.utc)
    if not user.company_id:
        company = ensure_default_company(session)
        user.company_id = company.id
    if not user.active_company_id:
        user.active_company_id = user.company_id
    session.commit()
    session.refresh(user)


def _validate_uniques(session: Session, *, phone: str | None, email: str | None, exclude_id: int | None = None) -> None:
    clauses = []
    if phone:
        clauses.append(User.phone == phone)
    if email:
        clauses.append(User.email == email)
    if not clauses:
        return

    query = select(User).where(or_(*clauses))
    if exclude_id is not None:
        query = query.where(User.id != exclude_id)
    if session.scalar(query):
        raise ConflictError("Ya existe un usuario con ese teléfono o correo.")


def create_user(session: Session, payload: UserCreate, *, actor: User | None = None) -> User:
    _validate_uniques(session, phone=payload.phone, email=payload.email)
    company = ensure_default_company(session)
    company_id = payload.company_id or getattr(actor, "company_id", None) or company.id
    active_company_id = payload.active_company_id or company_id
    user = User(
        company_id=company_id,
        active_company_id=active_company_id,
        name=payload.name,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        password_hash=get_password_hash(payload.password),
        role=payload.role.value,
        clickup_user_id=payload.clickup_user_id,
        weekly_salary=payload.weekly_salary,
        commission_percentage=payload.commission_percentage,
        is_active=payload.is_active,
        permissions=payload.permissions,
        notes=payload.notes,
    )
    session.add(user)
    log_action(
        session,
        actor=actor,
        action="users.create",
        entity_type="user",
        entity_id=None,
        description=f"Alta de usuario {payload.name}.",
        payload={"role": payload.role.value, "company_id": company_id},
    )
    session.commit()
    session.refresh(user)
    return user


def delete_user(session: Session, user_id: int, *, company_id: int | None = None, actor: User | None = None) -> None:
    user = get_user(session, user_id, company_id=company_id)
    log_action(
        session,
        actor=actor,
        action="users.delete",
        entity_type="user",
        entity_id=user.id,
        description=f"Eliminación de usuario {user.name}.",
    )
    session.delete(user)
    session.commit()


def update_user(session: Session, user_id: int, payload: UserUpdate, *, actor: User | None = None) -> User:
    user = get_user(session, user_id, company_id=getattr(actor, "company_id", None))
    data = payload.model_dump(exclude_unset=True)
    new_phone = data.get("phone", user.phone)
    new_email = str(data["email"]) if data.get("email") else data.get("email", user.email)
    _validate_uniques(session, phone=new_phone, email=new_email, exclude_id=user.id)

    for field, value in data.items():
        if field == "password" and value:
            user.password_hash = get_password_hash(value)
            continue
        if field == "role" and value is not None:
            setattr(user, field, value.value)
            continue
        if field == "email" and value is not None:
            setattr(user, field, str(value))
            continue
        setattr(user, field, value)

    if user.company_id and not user.active_company_id:
        user.active_company_id = user.company_id

    log_action(
        session,
        actor=actor,
        action="users.update",
        entity_type="user",
        entity_id=user.id,
        description=f"Actualización de usuario {user.name}.",
    )
    session.commit()
    session.refresh(user)
    return user
