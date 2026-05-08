from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Appointment, ServiceCatalog, User
from app.schemas.service_catalog import ServiceCatalogCreate, ServiceCatalogUpdate
from app.services.audit import log_action
from app.services.company_scope import company_user_ids
from app.services.exceptions import ConflictError, NotFoundError, ValidationError


def list_services(
    session: Session,
    *,
    include_deleted: bool = False,
    company_id: int | None = None,
    branch: str | None = None,
) -> list[ServiceCatalog]:
    query = select(ServiceCatalog).order_by(ServiceCatalog.sort_order, ServiceCatalog.name)
    if not include_deleted:
        query = query.where(ServiceCatalog.deleted_at.is_(None))
    if company_id is not None:
        query = query.where(
            or_(
                ServiceCatalog.created_by_user_id.is_(None),
                ServiceCatalog.created_by_user_id.in_(company_user_ids(company_id)),
            )
        )
    if branch is not None:
        query = query.where(ServiceCatalog.branch == branch)
    return list(session.scalars(query).all())


def get_service(session: Session, service_id: int, *, company_id: int | None = None) -> ServiceCatalog:
    query = select(ServiceCatalog).where(ServiceCatalog.id == service_id)
    if company_id is not None:
        query = query.where(
            or_(
                ServiceCatalog.created_by_user_id.is_(None),
                ServiceCatalog.created_by_user_id.in_(company_user_ids(company_id)),
            )
        )
    service = session.scalar(query)
    if not service or service.deleted_at is not None:
        raise NotFoundError("Servicio no encontrado.")
    return service


def _ensure_unique_name(
    session: Session,
    name: str,
    *,
    exclude_id: int | None = None,
    company_id: int | None = None,
    branch: str = "local",
) -> None:
    query = select(ServiceCatalog).where(ServiceCatalog.name == name, ServiceCatalog.branch == branch)
    if company_id is not None:
        query = query.where(
            or_(
                ServiceCatalog.created_by_user_id.is_(None),
                ServiceCatalog.created_by_user_id.in_(company_user_ids(company_id)),
            )
        )
    if exclude_id is not None:
        query = query.where(ServiceCatalog.id != exclude_id)
    if session.scalar(query):
        raise ConflictError("Ya existe un servicio con ese nombre.")


def create_service(session: Session, payload: ServiceCatalogCreate, *, actor: User | None = None) -> ServiceCatalog:
    company_id = getattr(actor, "company_id", None)
    _ensure_unique_name(session, payload.name, company_id=company_id, branch=payload.branch)
    service = ServiceCatalog(
        branch=payload.branch,
        name=payload.name,
        description=payload.description,
        base_price=payload.base_price,
        estimated_duration_minutes=payload.estimated_duration_minutes,
        service_type=payload.service_type.value,
        is_active=payload.is_active,
        subfamily_id=payload.subfamily_id,
        created_by_user_id=actor.id if actor else None,
        updated_by_user_id=actor.id if actor else None,
    )
    session.add(service)
    log_action(
        session,
        actor=actor,
        action="services.create",
        entity_type="service_catalog",
        entity_id=None,
        description=f"Alta de servicio {payload.name}.",
    )
    session.commit()
    session.refresh(service)
    return service


def update_service(
    session: Session,
    service_id: int,
    payload: ServiceCatalogUpdate,
    *,
    actor: User | None = None,
) -> ServiceCatalog:
    company_id = getattr(actor, "company_id", None)
    service = get_service(session, service_id, company_id=company_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        _ensure_unique_name(session, data["name"], exclude_id=service.id, company_id=company_id)
    for field, value in data.items():
        if field == "service_type" and value is not None:
            setattr(service, field, value.value)
            continue
        setattr(service, field, value)
    service.updated_by_user_id = actor.id if actor else None
    log_action(
        session,
        actor=actor,
        action="services.update",
        entity_type="service_catalog",
        entity_id=service.id,
        description=f"Actualizacion del servicio {service.name}.",
    )
    session.commit()
    session.refresh(service)
    return service


def soft_delete_service(session: Session, service_id: int, *, actor: User | None = None) -> ServiceCatalog:
    company_id = getattr(actor, "company_id", None)
    service = get_service(session, service_id, company_id=company_id)
    has_history = session.scalar(
        select(Appointment.id)
        .where(Appointment.service_catalog_id == service.id)
        .where(Appointment.deleted_at.is_(None))
        .limit(1)
    )
    if has_history:
        raise ValidationError("No puedes eliminar un servicio con historial; desactivalo en su lugar.")
    service.deleted_at = datetime.now(timezone.utc)
    service.deleted_by_user_id = actor.id if actor else None
    service.delete_reason = "Eliminacion logica desde panel/API."
    service.is_active = False
    log_action(
        session,
        actor=actor,
        action="services.delete",
        entity_type="service_catalog",
        entity_id=service.id,
        description=f"Baja logica del servicio {service.name}.",
    )
    session.commit()
    return service
