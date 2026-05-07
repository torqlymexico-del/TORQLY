from datetime import date

from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import PaymentMethod, UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.schemas.payment import PaymentCreate, PaymentExtraCreate
from app.services.exceptions import ServiceError
from app.services.payments import (
    create_payment,
    get_pending_charge_appointment,
    list_payments,
    list_pending_charge_appointments,
)


router = APIRouter(tags=["web-pos"])


@router.get("/pos")
def pos_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    appointment_id: int | None = Query(default=None),
):
    company_id = current_company_id(current_user)
    pending_appointments = list_pending_charge_appointments(db, company_id=company_id)
    selected = None
    if appointment_id:
        try:
            selected = get_pending_charge_appointment(db, appointment_id, company_id=company_id)
        except ServiceError:
            selected = None
    if selected is None and pending_appointments:
        selected = pending_appointments[0]
    recent_payments = list_payments(db, target_date=date.today(), company_id=company_id)[:8]
    return templates.TemplateResponse(
        request,
        "pos/index.html",
        base_context(
            request,
            current_user=current_user,
            pending_appointments=pending_appointments,
            selected_appointment=selected,
            recent_payments=recent_payments,
            page_title="POS",
        ),
    )


@router.post("/pos")
async def pos_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
):
    form = await request.form()
    try:
        appointment_id = int(form.get("appointment_id"))
        payment_method = PaymentMethod(form.get("payment_method"))
        discount_total = form.get("discount_total") or "0"
        notes = form.get("notes") or None
        reference = form.get("reference") or None

        extras: list[PaymentExtraCreate] = []
        descriptions = form.getlist("extra_description")
        quantities = form.getlist("extra_quantity")
        prices = form.getlist("extra_unit_price")
        commission_flags = form.getlist("extra_apply_commission")
        for index, description in enumerate(descriptions):
            cleaned = (description or "").strip()
            quantity = quantities[index] if index < len(quantities) else "1"
            price = prices[index] if index < len(prices) else "0"
            apply_commission = index < len(commission_flags) and commission_flags[index] == "true"
            if not cleaned:
                continue
            extras.append(
                PaymentExtraCreate(
                    description=cleaned,
                    quantity=quantity,
                    unit_price=price,
                    apply_commission=apply_commission,
                )
            )

        payment = create_payment(
            db,
            PaymentCreate(
                appointment_id=appointment_id,
                payment_method=payment_method,
                discount_total=discount_total,
                notes=notes,
                reference=reference,
                extras=extras,
            ),
            actor=current_user,
        )
        return redirect_with_message(
            f"/payments?payment_id={payment.id}",
            f"Pago {payment.ticket_number} registrado correctamente.",
        )
    except ServiceError as exc:
        appointment_id = form.get("appointment_id") or ""
        return redirect_with_message(f"/pos?appointment_id={appointment_id}", str(exc), "error")
