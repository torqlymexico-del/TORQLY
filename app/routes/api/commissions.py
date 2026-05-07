from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.schemas.commission import CommissionOperatorSummary, CommissionRead
from app.services.commissions import list_commissions, summarize_commissions_by_operator


router = APIRouter(prefix="/commissions", tags=["commissions"])


def _authorize_commission_access(current_user, operator_id: int) -> None:
    elevated_roles = {UserRole.ADMIN.value, UserRole.SUPERVISOR.value}
    if current_user.role not in elevated_roles and current_user.id != operator_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para consultar esas comisiones.",
        )


@router.get("/", response_model=list[CommissionRead])
def get_commissions(
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    operator_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[CommissionRead]:
    if operator_id is not None:
        _authorize_commission_access(current_user, operator_id)
    commissions = list_commissions(
        db,
        company_id=current_company_id(current_user),
        operator_id=operator_id,
        date_from=date_from,
        date_to=date_to,
    )
    return [
        CommissionRead(
            id=item.id,
            user_id=item.user_id,
            appointment_id=item.appointment_id,
            service_job_id=item.service_job_id,
            payment_id=item.payment_id,
            base_amount=item.base_amount,
            extra_amount=item.extra_amount,
            total_amount=item.total_amount,
            calculation_note=item.calculation_note,
            calculated_at=item.calculated_at,
            period_date=item.period_date,
            user_name=item.user.name if item.user else None,
        )
        for item in commissions
    ]


@router.get("/operators/{operator_id}", response_model=list[CommissionOperatorSummary])
def get_operator_commissions(
    operator_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    period: str = Query(default="daily", pattern="^(daily|weekly)$"),
    reference_date: date = Query(default_factory=date.today),
) -> list[CommissionOperatorSummary]:
    _authorize_commission_access(current_user, operator_id)
    if period == "weekly":
        date_from = reference_date - timedelta(days=reference_date.weekday())
        date_to = date_from + timedelta(days=6)
    else:
        date_from = reference_date
        date_to = reference_date
    return [
        CommissionOperatorSummary(**summary)
        for summary in summarize_commissions_by_operator(
            db,
            company_id=current_company_id(current_user),
            operator_id=operator_id,
            date_from=date_from,
            date_to=date_to,
            period=period,
        )
    ]
