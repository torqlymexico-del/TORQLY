from datetime import date, time
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import can_select_integrations_manually, current_company_id, require_roles
from app.enums import IntegrationAccountProvider
from app.enums import AppointmentOrigin, AppointmentStatus, UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services.integration_manager import list_accounts
from app.services.appointments import (
    cancel_appointment,
    create_appointment,
    get_appointment,
    list_appointments,
    soft_delete_appointment,
    update_appointment,
)
from app.services.clients import list_clients
from app.services.exceptions import ServiceError
from app.services.service_catalog import list_services
from app.services.users import list_assignable_operators
from app.services.vehicles import list_vehicles
from app.utils.dates import combine_local_date_time


router = APIRouter(prefix="/panel/citas", tags=["web-appointments"])


@router.get("")
def appointments_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    edit: int | None = None,
):
    if edit:
        try:
            selected = get_appointment(db, edit, company_id=current_company_id(current_user))
        except ServiceError as exc:
            return redirect_with_message("/panel/citas", str(exc), "error")
    else:
        selected = None
    return templates.TemplateResponse(
        request,
        "appointments/index.html",
        base_context(
            request,
            current_user=current_user,
            can_select_integrations=can_select_integrations_manually(current_user),
            appointments=list_appointments(db, company_id=current_company_id(current_user)),
            clients=list_clients(db, company_id=current_company_id(current_user)),
            vehicles=list_vehicles(db, company_id=current_company_id(current_user)),
            services=list_services(db, company_id=current_company_id(current_user)),
            operators=list_assignable_operators(db, company_id=current_company_id(current_user)),
            whatsapp_integrations=list_accounts(
                db,
                company_id=current_company_id(current_user) or 0,
                provider=IntegrationAccountProvider.WHATSAPP_META.value,
            ) if current_company_id(current_user) else [],
            google_calendar_integrations=list_accounts(
                db,
                company_id=current_company_id(current_user) or 0,
                provider=IntegrationAccountProvider.GOOGLE_CALENDAR.value,
            ) if current_company_id(current_user) else [],
            clickup_integrations=list_accounts(
                db,
                company_id=current_company_id(current_user) or 0,
                provider=IntegrationAccountProvider.CLICKUP.value,
            ) if current_company_id(current_user) else [],
            selected=selected,
            page_title="Citas",
        ),
    )


@router.post("")
def appointments_create(
    client_id: int = Form(...),
    vehicle_id: int = Form(...),
    service_catalog_id: int = Form(...),
    scheduled_date: date = Form(...),
    scheduled_time: time = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    operator_id: int | None = Form(default=None),
    whatsapp_integration_id: int | None = Form(default=None),
    google_calendar_integration_id: int | None = Form(default=None),
    clickup_integration_id: int | None = Form(default=None),
    address: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    status: str = Form(default=AppointmentStatus.PENDING.value),
    origin: str = Form(default=AppointmentOrigin.MANUAL.value),
    estimated_price: Decimal | None = Form(default=None),
):
    try:
        create_appointment(
            db,
            AppointmentCreate(
                client_id=client_id,
                vehicle_id=vehicle_id,
                service_catalog_id=service_catalog_id,
                operator_id=operator_id,
                whatsapp_integration_id=whatsapp_integration_id,
                google_calendar_integration_id=google_calendar_integration_id,
                clickup_integration_id=clickup_integration_id,
                scheduled_start=combine_local_date_time(scheduled_date, scheduled_time),
                address=address or None,
                notes=notes or None,
                status=AppointmentStatus(status),
                origin=AppointmentOrigin(origin),
                estimated_price=estimated_price,
            ),
            actor=current_user,
        )
        return redirect_with_message("/panel/citas", "Cita creada correctamente.")
    except ServiceError as exc:
        return redirect_with_message("/panel/citas", str(exc), "error")


@router.post("/{appointment_id}/editar")
def appointments_update(
    appointment_id: int,
    client_id: int = Form(...),
    vehicle_id: int = Form(...),
    service_catalog_id: int = Form(...),
    scheduled_date: date = Form(...),
    scheduled_time: time = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    operator_id: int | None = Form(default=None),
    whatsapp_integration_id: int | None = Form(default=None),
    google_calendar_integration_id: int | None = Form(default=None),
    clickup_integration_id: int | None = Form(default=None),
    address: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    status: str = Form(default=AppointmentStatus.PENDING.value),
    origin: str = Form(default=AppointmentOrigin.MANUAL.value),
    estimated_price: Decimal | None = Form(default=None),
):
    try:
        update_appointment(
            db,
            appointment_id,
            AppointmentUpdate(
                client_id=client_id,
                vehicle_id=vehicle_id,
                service_catalog_id=service_catalog_id,
                operator_id=operator_id,
                whatsapp_integration_id=whatsapp_integration_id,
                google_calendar_integration_id=google_calendar_integration_id,
                clickup_integration_id=clickup_integration_id,
                scheduled_start=combine_local_date_time(scheduled_date, scheduled_time),
                address=address or None,
                notes=notes or None,
                status=AppointmentStatus(status),
                origin=AppointmentOrigin(origin),
                estimated_price=estimated_price,
            ),
            actor=current_user,
        )
        return redirect_with_message("/panel/citas", "Cita actualizada.")
    except ServiceError as exc:
        return redirect_with_message(f"/panel/citas?edit={appointment_id}", str(exc), "error")


@router.post("/{appointment_id}/cancelar")
def appointments_cancel(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    reason: str | None = Form(default=None),
):
    try:
        cancel_appointment(db, appointment_id, actor=current_user, reason=reason)
        return redirect_with_message("/panel/citas", "Cita cancelada.")
    except ServiceError as exc:
        return redirect_with_message("/panel/citas", str(exc), "error")


@router.post("/{appointment_id}/eliminar")
def appointments_delete(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
):
    try:
        soft_delete_appointment(db, appointment_id, actor=current_user)
        return redirect_with_message("/panel/citas", "Cita enviada a baja lógica.")
    except ServiceError as exc:
        return redirect_with_message("/panel/citas", str(exc), "error")
