import random
import string
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import InviteCode, User
from app.services.exceptions import ConflictError, NotFoundError, ValidationError


def _random_code() -> str:
    chars = string.ascii_uppercase + string.digits
    # exclude easily confused characters
    chars = chars.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
    return "".join(random.choices(chars, k=8))


def generate_invite_code(
    session: Session,
    *,
    company_id: int,
    role: str,
    created_by_id: int,
    branch: str = "local",
    label: str | None = None,
) -> InviteCode:
    for _ in range(10):
        code = _random_code()
        if not session.scalar(select(InviteCode).where(InviteCode.code == code)):
            break
    invite = InviteCode(
        code=code,
        company_id=company_id,
        role=role,
        branch=branch,
        label=label,
        created_by_id=created_by_id,
    )
    session.add(invite)
    session.commit()
    session.refresh(invite)
    return invite


def list_invite_codes(session: Session, *, company_id: int) -> list[InviteCode]:
    return list(
        session.scalars(
            select(InviteCode)
            .where(InviteCode.company_id == company_id)
            .order_by(InviteCode.created_at.desc())
        ).all()
    )


def revoke_invite_code(session: Session, *, code_id: int, company_id: int) -> None:
    invite = session.scalar(
        select(InviteCode).where(InviteCode.id == code_id, InviteCode.company_id == company_id)
    )
    if not invite:
        raise NotFoundError("Código no encontrado.")
    if invite.used_at:
        raise ValidationError("El código ya fue usado y no se puede revocar.")
    session.delete(invite)
    session.commit()


def validate_and_use_invite_code(session: Session, *, code: str, user: User) -> InviteCode:
    invite = session.scalar(select(InviteCode).where(InviteCode.code == code.upper().strip()))
    if not invite:
        raise ValidationError("Código de acceso inválido.")
    if not invite.is_active:
        raise ValidationError("Este código ha sido revocado.")
    if invite.used_at is not None:
        raise ValidationError("Este código ya fue utilizado.")
    invite.used_by_id = user.id
    invite.used_at = datetime.now(timezone.utc)
    invite.is_active = False
    session.commit()
    session.refresh(invite)
    return invite


def any_users_exist(session: Session) -> bool:
    return (session.scalar(select(func.count(User.id))) or 0) > 0
