from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, get_current_user, require_roles
from app.enums import UserRole
from app.routes.api.common import raise_api_error
from app.schemas.payment import PaymentCreate, PaymentRead, PendingChargeAppointmentRead
from app.services.exceptions import ServiceError
from app.services.payments import (
    create_payment,
    get_payment,
    list_payments,
    list_pending_charge_appointments,
)


router = APIRouter(prefix="/payments", tags=["payments"])


def _serialize_payment(payment) -> PaymentRead:
    appointment = payment.appointment
    return PaymentRead(
        id=payment.id,
        appointment_id=payment.appointment_id,
        client_id=payment.client_id,
        cashier_id=payment.cashier_id,
        ticket_number=payment.ticket_number,
        reference=payment.reference,
        subtotal=payment.subtotal,
        extras_total=payment.extras_total,
        discount_total=payment.discount_total,
        total=payment.total,
        payment_method=payment.payment_method,
        notes=payment.notes,
        paid_at=payment.paid_at,
        items=payment.items,
        client_name=appointment.client.name if appointment and appointment.client else None,
        vehicle_label=(
            f"{appointment.vehicle.brand} {appointment.vehicle.model}"
            if appointment and appointment.vehicle
            else None
        ),
        service_name=appointment.service.name if appointment and appointment.service else None,
        operator_name=appointment.operator.name if appointment and appointment.operator else None,
        cashier_name=payment.cashier.name if payment.cashier else None,
    )


def _serialize_pending_appointment(appointment) -> PendingChargeAppointmentRead:
    return PendingChargeAppointmentRead(
        id=appointment.id,
        scheduled_start=appointment.scheduled_start,
        status=appointment.status,
        charge_status=appointment.charge_status,
        estimated_price=appointment.estimated_price,
        client_name=appointment.client.name if appointment.client else None,
        vehicle_label=(
            f"{appointment.vehicle.brand} {appointment.vehicle.model}" if appointment.vehicle else None
        ),
        service_name=appointment.service.name if appointment.service else None,
        operator_name=appointment.operator.name if appointment.operator else None,
    )


@router.get("/", response_model=list[PaymentRead])
def get_payments(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    target_date: date | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[PaymentRead]:
    return [
        _serialize_payment(payment)
        for payment in list_payments(
            db,
            target_date=target_date,
            date_from=date_from,
            date_to=date_to,
            company_id=current_company_id(current_user),
        )
    ]


@router.get("/pending-appointments", response_model=list[PendingChargeAppointmentRead])
def get_pending_appointments(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> list[PendingChargeAppointmentRead]:
    return [
        _serialize_pending_appointment(item)
        for item in list_pending_charge_appointments(db, company_id=current_company_id(current_user))
    ]


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment_detail(
    payment_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> PaymentRead:
    try:
        return _serialize_payment(get_payment(db, payment_id, company_id=current_company_id(current_user)))
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/", response_model=PaymentRead)
def create_payment_endpoint(
    payload: PaymentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
) -> PaymentRead:
    try:
        return _serialize_payment(create_payment(db, payload, actor=current_user))
    except ServiceError as exc:
        raise_api_error(exc)
