from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, User, Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.services.audit import log_action
from app.services.company_scope import created_by_company_clause
from app.services.exceptions import NotFoundError, ValidationError


def list_vehicles(
    session: Session,
    *,
    include_deleted: bool = False,
    company_id: int | None = None,
    branch: str | None = None,
) -> list[Vehicle]:
    query = select(Vehicle).order_by(Vehicle.brand, Vehicle.model)
    if not include_deleted:
        query = query.where(Vehicle.deleted_at.is_(None))
    query = query.where(created_by_company_clause(Vehicle, company_id))
    if branch is not None:
        query = query.where(Vehicle.branch == branch)
    return list(session.scalars(query).all())


def get_vehicle(session: Session, vehicle_id: int, *, company_id: int | None = None) -> Vehicle:
    vehicle = session.scalar(
        select(Vehicle)
        .where(Vehicle.id == vehicle_id)
        .where(created_by_company_clause(Vehicle, company_id))
    )
    if not vehicle or vehicle.deleted_at is not None:
        raise NotFoundError("Vehiculo no encontrado.")
    return vehicle


def _validate_client(session: Session, client_id: int, *, company_id: int | None = None) -> Client:
    client = session.scalar(
        select(Client)
        .where(Client.id == client_id)
        .where(created_by_company_clause(Client, company_id))
    )
    if not client or client.deleted_at is not None:
        raise ValidationError("El cliente seleccionado no existe o esta inactivo.")
    return client


def create_vehicle(session: Session, payload: VehicleCreate, *, actor: User | None = None) -> Vehicle:
    if payload.client_id is not None:
        _validate_client(session, payload.client_id, company_id=getattr(actor, "company_id", None))
    vehicle = Vehicle(
        client_id=payload.client_id,
        branch=payload.branch,
        brand=payload.brand,
        model=payload.model,
        type=payload.type,
        year=payload.year,
        color=payload.color,
        plates=payload.plates,
        notes=payload.notes,
        is_active=payload.is_active,
        created_by_user_id=actor.id if actor else None,
        updated_by_user_id=actor.id if actor else None,
    )
    session.add(vehicle)
    log_action(
        session,
        actor=actor,
        action="vehicles.create",
        entity_type="vehicle",
        entity_id=None,
        description=f"Alta de vehiculo {payload.brand} {payload.model}.",
    )
    session.commit()
    session.refresh(vehicle)
    return vehicle


def update_vehicle(session: Session, vehicle_id: int, payload: VehicleUpdate, *, actor: User | None = None) -> Vehicle:
    vehicle = get_vehicle(session, vehicle_id, company_id=getattr(actor, "company_id", None))
    data = payload.model_dump(exclude_unset=True)
    if "client_id" in data and data["client_id"] is not None:
        _validate_client(session, data["client_id"], company_id=getattr(actor, "company_id", None))
    for field, value in data.items():
        setattr(vehicle, field, value)
    vehicle.updated_by_user_id = actor.id if actor else None
    log_action(
        session,
        actor=actor,
        action="vehicles.update",
        entity_type="vehicle",
        entity_id=vehicle.id,
        description=f"Actualizacion de vehiculo {vehicle.brand} {vehicle.model}.",
    )
    session.commit()
    session.refresh(vehicle)
    return vehicle


def soft_delete_vehicle(session: Session, vehicle_id: int, *, actor: User | None = None) -> Vehicle:
    vehicle = get_vehicle(session, vehicle_id, company_id=getattr(actor, "company_id", None))
    vehicle.deleted_at = datetime.now(timezone.utc)
    vehicle.deleted_by_user_id = actor.id if actor else None
    vehicle.delete_reason = "Eliminacion logica desde panel/API."
    vehicle.is_active = False
    log_action(
        session,
        actor=actor,
        action="vehicles.delete",
        entity_type="vehicle",
        entity_id=vehicle.id,
        description=f"Baja logica del vehiculo {vehicle.brand} {vehicle.model}.",
    )
    session.commit()
    return vehicle
