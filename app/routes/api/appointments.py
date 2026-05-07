from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.api.common import raise_api_error
from app.schemas.appointment import AppointmentCreate, AppointmentRead, AppointmentUpdate
from app.services.appointments import (
    agenda_for_day,
    cancel_appointment,
    create_appointment,
    get_appointment,
    list_appointments,
    soft_delete_appointment,
    update_appointment,
)
from app.services.exceptions import ServiceError


router = APIRouter(prefix="/appointments", tags=["appointments"])


def _serialize(appointment) -> AppointmentRead:
    return AppointmentRead(
        id=appointment.id,
        client_id=appointment.client_id,
        vehicle_id=appointment.vehicle_id,
        service_catalog_id=appointment.service_catalog_id,
        operator_id=appointment.operator_id,
        scheduled_start=appointment.scheduled_start,
        address=appointment.address,
        notes=appointment.notes,
        status=appointment.status,
        origin=appointment.origin,
        charge_status=appointment.charge_status,
        paid_at=appointment.paid_at,
        estimated_price=appointment.estimated_price,
        google_event_id=appointment.google_event_id,
        clickup_task_id=appointment.clickup_task_id,
        clickup_task_url=appointment.clickup_task_url,
        whatsapp_integration_id=appointment.whatsapp_integration_id,
        google_calendar_integration_id=appointment.google_calendar_integration_id,
        google_sheets_integration_id=appointment.google_sheets_integration_id,
        clickup_integration_id=appointment.clickup_integration_id,
        meta_business_integration_id=appointment.meta_business_integration_id,
        client_name=appointment.client.name if appointment.client else None,
        vehicle_label=f"{appointment.vehicle.brand} {appointment.vehicle.model}" if appointment.vehicle else None,
        service_name=appointment.service.name if appointment.service else None,
        operator_name=appointment.operator.name if appointment.operator else None,
    )


@router.get("/", response_model=list[AppointmentRead])
def get_appointments(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> list[AppointmentRead]:
    return [
        _serialize(item)
        for item in list_appointments(
            db,
            start_date=start_date,
            end_date=end_date,
            company_id=current_company_id(current_user),
        )
    ]


@router.get("/agenda/day", response_model=list[AppointmentRead])
def get_day_agenda(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    target_date: date = Query(...),
) -> list[AppointmentRead]:
    return [
        _serialize(item)
        for item in agenda_for_day(db, target_date=target_date, company_id=current_company_id(current_user))
    ]


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment_detail(
    appointment_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> AppointmentRead:
    try:
        return _serialize(get_appointment(db, appointment_id, company_id=current_company_id(current_user)))
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/", response_model=AppointmentRead)
def create_appointment_endpoint(
    payload: AppointmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> AppointmentRead:
    try:
        return _serialize(create_appointment(db, payload, actor=current_user))
    except ServiceError as exc:
        raise_api_error(exc)


@router.put("/{appointment_id}", response_model=AppointmentRead)
def update_appointment_endpoint(
    appointment_id: int,
    payload: AppointmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> AppointmentRead:
    try:
        return _serialize(update_appointment(db, appointment_id, payload, actor=current_user))
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_appointment_endpoint(
    appointment_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    reason: str | None = Query(default=None),
) -> AppointmentRead:
    try:
        return _serialize(cancel_appointment(db, appointment_id, actor=current_user, reason=reason))
    except ServiceError as exc:
        raise_api_error(exc)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_appointment_endpoint(
    appointment_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
) -> Response:
    try:
        soft_delete_appointment(db, appointment_id, actor=current_user)
    except ServiceError as exc:
        raise_api_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
