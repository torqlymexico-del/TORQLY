from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.models import User
from app.routes.api.common import raise_api_error
from app.services.exceptions import ServiceError
from app.services.payroll_service import (
    add_deduction, get_operator_summary, get_payroll_setting,
    list_operators, pay_commissions, pay_salary, update_payroll_setting,
)


router = APIRouter(prefix="/payroll", tags=["payroll"])


class SettingIn(BaseModel):
    rag_unit_price: Decimal


class DeductionIn(BaseModel):
    user_id: int
    deduction_type: str = "trapos"
    quantity: int = 1
    unit_amount: Decimal
    notes: str | None = None


class CommissionPaymentIn(BaseModel):
    user_id: int
    amount: Decimal
    payment_source: str = "efectivo"
    cash_session_id: int | None = None
    notes: str | None = None


class SalaryPaymentIn(BaseModel):
    user_id: int
    amount: Decimal
    payment_source: str = "efectivo"
    cash_session_id: int | None = None
    notes: str | None = None


class SettingOut(BaseModel):
    id: int
    company_id: int | None
    rag_unit_price: Decimal
    model_config = {"from_attributes": True}


class DeductionOut(BaseModel):
    id: int
    user_id: int
    deduction_type: str
    quantity: int
    unit_amount: Decimal
    total_amount: Decimal
    notes: str | None = None
    model_config = {"from_attributes": True}


class OperatorOut(BaseModel):
    id: int
    name: str
    role: str
    commission_percentage: Decimal
    weekly_salary: Decimal
    model_config = {"from_attributes": True}


@router.get("/operators", response_model=list[OperatorOut])
def get_operators(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    return [OperatorOut.model_validate(u) for u in list_operators(db, company_id=current_company_id(current_user))]


@router.get("/operators/{user_id}/summary")
def get_summary(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    try:
        return get_operator_summary(db, user_id, current_company_id(current_user))
    except ServiceError as exc:
        raise_api_error(exc)


@router.get("/settings", response_model=SettingOut)
def get_settings(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    return SettingOut.model_validate(get_payroll_setting(db, current_company_id(current_user)))


@router.put("/settings", response_model=SettingOut)
def update_settings(
    payload: SettingIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
):
    return SettingOut.model_validate(update_payroll_setting(db, rag_unit_price=payload.rag_unit_price, company_id=current_company_id(current_user)))


@router.post("/deductions", response_model=DeductionOut)
def create_deduction(
    payload: DeductionIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    try:
        d = add_deduction(
            db,
            user_id=payload.user_id,
            deduction_type=payload.deduction_type,
            quantity=payload.quantity,
            unit_amount=payload.unit_amount,
            notes=payload.notes,
            actor=current_user,
        )
        return DeductionOut.model_validate(d)
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/pay-commission")
def pay_commission_endpoint(
    payload: CommissionPaymentIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    try:
        cp = pay_commissions(
            db,
            user_id=payload.user_id,
            amount=payload.amount,
            payment_source=payload.payment_source,
            cash_session_id=payload.cash_session_id,
            notes=payload.notes,
            actor=current_user,
        )
        return {"id": cp.id, "user_id": cp.user_id, "amount": float(cp.amount)}
    except ServiceError as exc:
        raise_api_error(exc)


@router.post("/pay-salary")
def pay_salary_endpoint(
    payload: SalaryPaymentIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
):
    try:
        sp = pay_salary(
            db,
            user_id=payload.user_id,
            amount=payload.amount,
            payment_source=payload.payment_source,
            cash_session_id=payload.cash_session_id,
            notes=payload.notes,
            actor=current_user,
        )
        return {"id": sp.id, "user_id": sp.user_id, "amount": float(sp.amount)}
    except ServiceError as exc:
        raise_api_error(exc)
