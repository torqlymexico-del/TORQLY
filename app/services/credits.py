from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import CreditMovementType
from app.models import ClientCreditAccount, ClientCreditMovement, User
from app.services.exceptions import ConflictError, NotFoundError, ValidationError


def get_or_create_account(
    session: Session, client_id: int, *, credit_limit: Decimal = Decimal(0), actor: User
) -> ClientCreditAccount:
    account = session.scalar(
        select(ClientCreditAccount).where(ClientCreditAccount.client_id == client_id)
    )
    if account:
        return account

    account = ClientCreditAccount(
        client_id=client_id,
        credit_limit=credit_limit,
        current_balance=Decimal(0),
        is_active=True,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def update_credit_limit(
    session: Session, client_id: int, *, credit_limit: Decimal, is_active: bool, notes: str | None, actor: User
) -> ClientCreditAccount:
    account = _get_account(session, client_id)
    account.credit_limit = credit_limit
    account.is_active = is_active
    if notes is not None:
        account.notes = notes
    session.commit()
    session.refresh(account)
    return account


def add_charge(
    session: Session,
    client_id: int,
    *,
    amount: Decimal,
    order_id: int | None = None,
    description: str | None = None,
    actor: User,
) -> ClientCreditMovement:
    account = _get_account(session, client_id)
    if not account.is_active:
        raise ValidationError("La cuenta de crédito está inactiva.")
    if account.current_balance + amount > account.credit_limit:
        raise ValidationError(
            f"Excede el límite de crédito. Disponible: ${account.credit_limit - account.current_balance:.2f}"
        )

    account.current_balance += amount
    mv = ClientCreditMovement(
        account_id=account.id,
        client_id=client_id,
        order_id=order_id,
        movement_type=CreditMovementType.CHARGE.value,
        amount=amount,
        description=description or "Cargo a crédito",
        created_by_id=actor.id,
    )
    session.add(mv)
    session.commit()
    session.refresh(mv)
    return mv


def add_payment(
    session: Session,
    client_id: int,
    *,
    amount: Decimal,
    description: str | None = None,
    actor: User,
) -> ClientCreditMovement:
    account = _get_account(session, client_id)
    if amount > account.current_balance:
        raise ValidationError("El pago excede el saldo adeudado.")

    account.current_balance -= amount
    mv = ClientCreditMovement(
        account_id=account.id,
        client_id=client_id,
        movement_type=CreditMovementType.PAYMENT.value,
        amount=amount,
        description=description or "Pago de crédito",
        created_by_id=actor.id,
    )
    session.add(mv)
    session.commit()
    session.refresh(mv)
    return mv


def list_movements(
    session: Session, client_id: int, *, limit: int = 100
) -> list[ClientCreditMovement]:
    account = session.scalar(
        select(ClientCreditAccount).where(ClientCreditAccount.client_id == client_id)
    )
    if not account:
        return []
    return list(
        session.scalars(
            select(ClientCreditMovement)
            .where(ClientCreditMovement.account_id == account.id)
            .order_by(ClientCreditMovement.created_at.desc())
            .limit(limit)
        ).all()
    )


def list_accounts(session: Session, *, company_user_ids: list[int] | None = None) -> list[ClientCreditAccount]:
    q = select(ClientCreditAccount).where(ClientCreditAccount.is_active.is_(True))
    return list(session.scalars(q).all())


def _get_account(session: Session, client_id: int) -> ClientCreditAccount:
    account = session.scalar(
        select(ClientCreditAccount).where(ClientCreditAccount.client_id == client_id)
    )
    if not account:
        raise NotFoundError("El cliente no tiene cuenta de crédito.")
    return account
