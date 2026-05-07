from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.services.exceptions import ServiceError
from app.services.payments import get_payment, list_payments, payment_ticket_summary


router = APIRouter(tags=["web-payments"])


@router.get("/payments")
def payments_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.SUPERVISOR)),
    target_date: date = Query(default_factory=date.today),
    payment_id: int | None = Query(default=None),
):
    company_id = current_company_id(current_user)
    payments = list_payments(db, target_date=target_date, company_id=company_id)
    selected_payment = None
    ticket = None
    if payment_id:
        try:
            selected_payment = get_payment(db, payment_id, company_id=company_id)
            ticket = payment_ticket_summary(selected_payment)
        except ServiceError as exc:
            return redirect_with_message("/payments", str(exc), "error")
    elif payments:
        selected_payment = payments[0]
        ticket = payment_ticket_summary(selected_payment)

    return templates.TemplateResponse(
        request,
        "payments/index.html",
        base_context(
            request,
            current_user=current_user,
            payments=payments,
            selected_payment=selected_payment,
            ticket=ticket,
            target_date=target_date,
            page_title="Pagos",
        ),
    )
