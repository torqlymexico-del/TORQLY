from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, User
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.audit import log_action
from app.services.company_scope import created_by_company_clause
from app.services.exceptions import NotFoundError


def list_clients(
    session: Session,
    *,
    include_deleted: bool = False,
    company_id: int | None = None,
    branch: str | None = None,
) -> list[Client]:
    query = select(Client).order_by(Client.name)
    if not include_deleted:
        query = query.where(Client.deleted_at.is_(None))
    query = query.where(created_by_company_clause(Client, company_id))
    if branch is not None:
        query = query.where(Client.branch == branch)
    return list(session.scalars(query).all())


def get_client(session: Session, client_id: int, *, company_id: int | None = None) -> Client:
    client = session.scalar(
        select(Client)
        .where(Client.id == client_id)
        .where(created_by_company_clause(Client, company_id))
    )
    if not client or client.deleted_at is not None:
        raise NotFoundError("Cliente no encontrado.")
    return client


def create_client(session: Session, payload: ClientCreate, *, actor: User | None = None) -> Client:
    client = Client(
        name=payload.name,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        address=payload.address,
        notes=payload.notes,
        is_active=payload.is_active,
        branch=getattr(payload, "branch", "local"),
        created_by_user_id=actor.id if actor else None,
        updated_by_user_id=actor.id if actor else None,
    )
    session.add(client)
    log_action(
        session,
        actor=actor,
        action="clients.create",
        entity_type="client",
        entity_id=None,
        description=f"Alta de cliente {payload.name}.",
    )
    session.commit()
    session.refresh(client)
    return client


def update_client(session: Session, client_id: int, payload: ClientUpdate, *, actor: User | None = None) -> Client:
    client = get_client(session, client_id, company_id=getattr(actor, "company_id", None))
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "email" and value is not None:
            setattr(client, field, str(value))
            continue
        setattr(client, field, value)
    client.updated_by_user_id = actor.id if actor else None
    log_action(
        session,
        actor=actor,
        action="clients.update",
        entity_type="client",
        entity_id=client.id,
        description=f"Actualización de cliente {client.name}.",
    )
    session.commit()
    session.refresh(client)
    return client


def soft_delete_client(session: Session, client_id: int, *, actor: User | None = None) -> Client:
    client = get_client(session, client_id, company_id=getattr(actor, "company_id", None))
    client.deleted_at = datetime.now(timezone.utc)
    client.deleted_by_user_id = actor.id if actor else None
    client.delete_reason = "Eliminación lógica desde panel/API."
    client.is_active = False
    log_action(
        session,
        actor=actor,
        action="clients.delete",
        entity_type="client",
        entity_id=client.id,
        description=f"Cliente {client.name} enviado a baja lógica.",
    )
    session.commit()
    return client
