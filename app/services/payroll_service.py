from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CommissionPayment, PayrollDeduction, PayrollSetting, SalaryPayment, ServiceOrderWasher, User
from app.services.exceptions import NotFoundError


def get_payroll_setting(session: Session, company_id: int | None) -> PayrollSetting:
    setting = session.scalar(
        select(PayrollSetting).where(PayrollSetting.company_id == company_id)
    )
    if not setting:
        setting = PayrollSetting(company_id=company_id, rag_unit_price=Decimal(20))
        session.add(setting)
        session.commit()
        session.refresh(setting)
    return setting


def update_payroll_setting(
    session: Session, *, rag_unit_price: Decimal, company_id: int | None
) -> PayrollSetting:
    setting = get_payroll_setting(session, company_id)
    setting.rag_unit_price = rag_unit_price
    session.commit()
    session.refresh(setting)
    return setting


def get_operator_summary(session: Session, user_id: int, company_id: int | None) -> dict:
    user = session.get(User, user_id)
    if not user:
        raise NotFoundError("Operador no encontrado.")

    # Unpaid commissions from service order washers
    unpaid_washers = list(
        session.scalars(
            select(ServiceOrderWasher)
            .where(ServiceOrderWasher.user_id == user_id)
            .where(ServiceOrderWasher.is_paid.is_(False))
        ).all()
    )
    pending_commission = sum(w.commission_amount for w in unpaid_washers)

    # Deductions
    deductions = list(
        session.scalars(
            select(PayrollDeduction)
            .where(PayrollDeduction.user_id == user_id)
            .order_by(PayrollDeduction.created_at.desc())
            .limit(50)
        ).all()
    )
    total_deductions = sum(d.total_amount for d in deductions)

    return {
        "user_id": user_id,
        "name": user.name,
        "role": user.role,
        "weekly_salary": float(user.weekly_salary or 0),
        "commission_percentage": float(user.commission_percentage or 0),
        "pending_commission": float(pending_commission),
        "total_deductions": float(total_deductions),
        "net_commission": float(pending_commission - total_deductions),
        "deductions": deductions,
    }


def add_deduction(
    session: Session,
    *,
    user_id: int,
    deduction_type: str,
    quantity: int,
    unit_amount: Decimal,
    notes: str | None,
    actor: User,
) -> PayrollDeduction:
    d = PayrollDeduction(
        user_id=user_id,
        deduction_type=deduction_type,
        quantity=quantity,
        unit_amount=unit_amount,
        total_amount=unit_amount * quantity,
        notes=notes,
        created_by_id=actor.id,
    )
    session.add(d)
    session.commit()
    session.refresh(d)
    return d


def pay_commissions(
    session: Session,
    *,
    user_id: int,
    amount: Decimal,
    payment_source: str,
    cash_session_id: int | None,
    notes: str | None,
    actor: User,
) -> CommissionPayment:
    # Mark washer records as paid
    unpaid = list(
        session.scalars(
            select(ServiceOrderWasher)
            .where(ServiceOrderWasher.user_id == user_id)
            .where(ServiceOrderWasher.is_paid.is_(False))
        ).all()
    )
    for w in unpaid:
        w.is_paid = True
        w.paid_by_id = actor.id

    cp = CommissionPayment(
        user_id=user_id,
        amount=amount,
        payment_source=payment_source,
        cash_session_id=cash_session_id,
        notes=notes,
        paid_by_id=actor.id,
    )
    session.add(cp)
    session.commit()
    session.refresh(cp)
    return cp


def pay_salary(
    session: Session,
    *,
    user_id: int,
    amount: Decimal,
    payment_source: str,
    cash_session_id: int | None,
    notes: str | None,
    actor: User,
) -> SalaryPayment:
    sp = SalaryPayment(
        user_id=user_id,
        amount=amount,
        payment_source=payment_source,
        cash_session_id=cash_session_id,
        notes=notes,
        paid_by_id=actor.id,
    )
    session.add(sp)
    session.commit()
    session.refresh(sp)
    return sp


def list_operators(session: Session, *, company_id: int | None) -> list[User]:
    q = select(User).where(User.is_active.is_(True)).where(User.role.in_(["operator", "admin", "supervisor"]))
    if company_id is not None:
        q = q.where(User.company_id == company_id)
    return list(session.scalars(q).all())
