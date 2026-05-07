from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.enums import AppointmentStatus
from app.models import Appointment, InventoryProduct
from app.services.cash_cuts import create_or_refresh_cash_cut
from app.services.notifications import (
    notify_appointment_reminder,
    notify_daily_close_generated,
    notify_low_stock,
    notify_operator_reminder,
    notify_service_ready_for_charge,
)
from app.utils.dates import local_now


def _appointment_automation_query():
    return (
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.vehicle),
            joinedload(Appointment.service),
            joinedload(Appointment.operator),
            joinedload(Appointment.service_job),
        )
        .where(Appointment.deleted_at.is_(None))
        .where(Appointment.status.in_([AppointmentStatus.PENDING.value, AppointmentStatus.CONFIRMED.value]))
    )


def run_upcoming_appointment_automations(session: Session, *, now=None) -> dict:
    current_time = now or local_now()
    appointment_window_start = current_time + timedelta(minutes=55)
    appointment_window_end = current_time + timedelta(minutes=65)
    operator_window_start = current_time + timedelta(minutes=25)
    operator_window_end = current_time + timedelta(minutes=35)

    client_reminders = list(
        session.scalars(
            _appointment_automation_query()
            .where(Appointment.reminder_sent_at.is_(None))
            .where(Appointment.scheduled_start >= appointment_window_start)
            .where(Appointment.scheduled_start <= appointment_window_end)
            .order_by(Appointment.scheduled_start.asc(), Appointment.id.asc())
        ).unique().all()
    )
    operator_reminders = list(
        session.scalars(
            _appointment_automation_query()
            .where(Appointment.operator_id.is_not(None))
            .where(Appointment.operator_reminder_sent_at.is_(None))
            .where(Appointment.scheduled_start >= operator_window_start)
            .where(Appointment.scheduled_start <= operator_window_end)
            .order_by(Appointment.scheduled_start.asc(), Appointment.id.asc())
        ).unique().all()
    )

    client_count = 0
    operator_count = 0

    from app.services.whatsapp_conversations import send_automation_message

    for appointment in client_reminders:
        notify_appointment_reminder(session, appointment)
        if appointment.client and appointment.client.phone:
            send_automation_message(
                session,
                phone=appointment.client.phone,
                display_name=appointment.client.name if appointment.client else None,
                body=(
                    f"Recordatorio: tu cita #{appointment.id} inicia a las "
                    f"{appointment.scheduled_start.strftime('%H:%M')}."
                ),
                appointment=appointment,
            )
        appointment.reminder_sent_at = current_time
        client_count += 1

    for appointment in operator_reminders:
        notify_operator_reminder(session, appointment)
        if appointment.operator and appointment.operator.phone:
            send_automation_message(
                session,
                phone=appointment.operator.phone,
                display_name=appointment.operator.name if appointment.operator else None,
                body=(
                    f"Recordatorio interno: la cita #{appointment.id} con "
                    f"{appointment.client.name if appointment.client else 'cliente'} inicia a las "
                    f"{appointment.scheduled_start.strftime('%H:%M')}."
                ),
                appointment=appointment,
            )
        appointment.operator_reminder_sent_at = current_time
        operator_count += 1

    session.commit()
    return {"client_reminders": client_count, "operator_reminders": operator_count}


def handle_service_finished_automation(session: Session, appointment: Appointment) -> dict:
    if appointment.ready_for_charge_notified_at is not None:
        return {"status": "skipped", "reason": "already_notified"}
    if appointment.status != AppointmentStatus.FINISHED.value:
        return {"status": "skipped", "reason": "appointment_not_finished"}

    from app.services.whatsapp_conversations import send_automation_message

    if appointment.client and appointment.client.phone:
        send_automation_message(
            session,
            phone=appointment.client.phone,
            display_name=appointment.client.name if appointment.client else None,
            body="Tu vehiculo ya esta listo.",
            appointment=appointment,
        )

    notify_service_ready_for_charge(session, appointment)
    appointment.ready_for_charge_notified_at = local_now()
    session.commit()
    return {"status": "ok", "appointment_id": appointment.id}


def run_daily_close_automation(session: Session, *, target_date: date | None = None) -> dict:
    report_date = target_date or local_now().date()
    notes = "Resumen diario sugerido generado automaticamente por scheduler."
    cash_cut = create_or_refresh_cash_cut(
        session,
        target_date=report_date,
        actor=None,
        close_cut=False,
        notes=notes,
    )
    notify_daily_close_generated(session, cash_cut)

    export_result = {"status": "skipped", "message": "Google Sheets no configurado."}
    try:
        from app.integrations.google.sheets import export_daily_cut

        export_result = export_daily_cut(session, target_date=report_date)
    except Exception as exc:  # pragma: no cover - defensive branch
        export_result = {"status": "error", "message": str(exc)}
    session.commit()
    return {
        "status": "ok",
        "cash_cut_id": cash_cut.id,
        "cut_date": cash_cut.cut_date.isoformat(),
        "google_sheets": export_result,
    }


def run_low_stock_monitor(session: Session) -> dict:
    products = list(
        session.scalars(
            select(InventoryProduct)
            .where(InventoryProduct.deleted_at.is_(None))
            .where(InventoryProduct.is_active.is_(True))
            .order_by(InventoryProduct.name.asc())
        ).all()
    )

    low_stock_count = 0
    now = local_now()
    for product in products:
        if product.stock <= product.minimum_stock:
            if product.low_stock_notified_at is None:
                notify_low_stock(session, product)
                product.low_stock_notified_at = now
                low_stock_count += 1
        elif product.low_stock_notified_at is not None:
            product.low_stock_notified_at = None

    session.commit()
    return {"status": "ok", "new_alerts": low_stock_count}
