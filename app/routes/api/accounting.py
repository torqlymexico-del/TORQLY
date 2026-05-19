from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import UserRole
from app.models import User
from app.models.accounting import (
    AccountingEquityMovement,
    AccountingFixedAsset,
    AccountingFixedCost,
    AccountingPayable,
    AccountingSettings,
)


router = APIRouter(prefix="/accounting", tags=["accounting"])

PAYROLL_BASIS_OPTIONS = ("weekly_current", "manual_closing")
PAYABLE_STATUSES = ("pending", "partial", "paid", "cancelled")
EQUITY_TYPES = ("contribution", "withdrawal", "adjustment")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_settings(db: Session, company_id: int) -> AccountingSettings:
    settings = db.get(AccountingSettings, company_id)
    if not settings:
        settings = AccountingSettings(company_id=company_id)
        db.add(settings)
        db.flush()
    return settings


def _require_company(current_user) -> int:
    cid = current_company_id(current_user)
    if not cid:
        raise HTTPException(status_code=403, detail="Sin empresa activa.")
    return cid


# ── Schemas ───────────────────────────────────────────────────────────────────

class SettingsIn(BaseModel):
    vat_rate: Decimal = Decimal("16.00")
    monthly_depreciation: Decimal = Decimal("0.00")
    monthly_external_fees: Decimal = Decimal("0.00")
    target_net_margin: Decimal = Decimal("15.00")
    closing_day: int = 1
    opening_retained_earnings: Decimal = Decimal("0.00")
    opening_retained_earnings_notes: str | None = None
    opening_cash_balance: Decimal = Decimal("0.00")
    opening_cash_balance_date: date | None = None
    opening_domicilios_balance: Decimal = Decimal("0.00")
    opening_domicilios_balance_date: date | None = None
    payroll_liability_basis: str = "weekly_current"
    payroll_liability_manual: Decimal = Decimal("0.00")
    cleanup_notes: str | None = None
    notes: str | None = None


class FixedCostIn(BaseModel):
    name: str
    category: str = "General"
    monthly_amount: Decimal
    sort_order: int = 0
    is_active: bool = True


class FixedAssetIn(BaseModel):
    asset_name: str
    category: str = "Activo fijo"
    acquisition_date: date
    acquisition_cost: Decimal
    salvage_value: Decimal = Decimal("0.00")
    useful_life_months: int = 60
    notes: str | None = None


class PayableIn(BaseModel):
    vendor_name: str
    concept: str
    category: str = "General"
    due_date: date | None = None
    amount: Decimal
    notes: str | None = None


class PayableUpdateIn(BaseModel):
    status: str
    paid_amount: Decimal = Decimal("0.00")
    payment_method: str | None = None
    notes: str | None = None


class EquityMovementIn(BaseModel):
    movement_type: str = "contribution"
    concept: str
    amount: Decimal
    movement_date: date
    notes: str | None = None


# ── Settings ──────────────────────────────────────────────────────────────────

@router.get("/settings")
def get_settings(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
) -> dict:
    company_id = _require_company(current_user)
    settings = _get_or_create_settings(db, company_id)
    db.commit()
    return {
        "company_id": settings.company_id,
        "vat_rate": str(settings.vat_rate),
        "monthly_depreciation": str(settings.monthly_depreciation),
        "monthly_external_fees": str(settings.monthly_external_fees),
        "target_net_margin": str(settings.target_net_margin),
        "closing_day": settings.closing_day,
        "opening_retained_earnings": str(settings.opening_retained_earnings),
        "opening_retained_earnings_notes": settings.opening_retained_earnings_notes,
        "opening_cash_balance": str(settings.opening_cash_balance),
        "opening_cash_balance_date": str(settings.opening_cash_balance_date) if settings.opening_cash_balance_date else None,
        "opening_domicilios_balance": str(settings.opening_domicilios_balance),
        "opening_domicilios_balance_date": str(settings.opening_domicilios_balance_date) if settings.opening_domicilios_balance_date else None,
        "payroll_liability_basis": settings.payroll_liability_basis,
        "payroll_liability_manual": str(settings.payroll_liability_manual),
        "cleanup_notes": settings.cleanup_notes,
        "notes": settings.notes,
    }


@router.put("/settings")
def update_settings(
    payload: SettingsIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> dict:
    company_id = _require_company(current_user)
    settings = _get_or_create_settings(db, company_id)

    basis = payload.payroll_liability_basis
    if basis not in PAYROLL_BASIS_OPTIONS:
        basis = "weekly_current"

    closing_day = max(1, min(28, payload.closing_day))

    settings.vat_rate = payload.vat_rate
    settings.monthly_depreciation = payload.monthly_depreciation
    settings.monthly_external_fees = payload.monthly_external_fees
    settings.target_net_margin = payload.target_net_margin
    settings.closing_day = closing_day
    settings.opening_retained_earnings = payload.opening_retained_earnings
    settings.opening_retained_earnings_notes = payload.opening_retained_earnings_notes
    settings.opening_cash_balance = payload.opening_cash_balance
    settings.opening_cash_balance_date = payload.opening_cash_balance_date
    settings.opening_domicilios_balance = payload.opening_domicilios_balance
    settings.opening_domicilios_balance_date = payload.opening_domicilios_balance_date
    settings.payroll_liability_basis = basis
    settings.payroll_liability_manual = payload.payroll_liability_manual
    settings.cleanup_notes = payload.cleanup_notes
    settings.notes = payload.notes

    db.commit()
    db.refresh(settings)
    return {"ok": True}


# ── Fixed Costs ───────────────────────────────────────────────────────────────

@router.get("/fixed-costs")
def list_fixed_costs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
) -> list[dict]:
    company_id = _require_company(current_user)
    rows = list(db.scalars(
        select(AccountingFixedCost)
        .where(AccountingFixedCost.company_id == company_id)
        .order_by(AccountingFixedCost.sort_order.asc(), AccountingFixedCost.name.asc())
    ).all())
    return [
        {
            "id": r.id, "name": r.name, "category": r.category,
            "monthly_amount": str(r.monthly_amount), "sort_order": r.sort_order,
            "is_active": r.is_active,
        }
        for r in rows
    ]


@router.post("/fixed-costs")
def create_fixed_cost(
    payload: FixedCostIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> dict:
    company_id = _require_company(current_user)
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es requerido.")
    if payload.monthly_amount <= 0:
        raise HTTPException(status_code=422, detail="El monto mensual debe ser mayor a cero.")
    row = AccountingFixedCost(
        company_id=company_id,
        name=payload.name.strip(),
        category=payload.category.strip() or "General",
        monthly_amount=payload.monthly_amount,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "monthly_amount": str(row.monthly_amount)}


@router.put("/fixed-costs/{cost_id}")
def update_fixed_cost(
    cost_id: int,
    payload: FixedCostIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> dict:
    company_id = _require_company(current_user)
    row = db.get(AccountingFixedCost, cost_id)
    if not row or row.company_id != company_id:
        raise HTTPException(status_code=404, detail="Costo fijo no encontrado.")
    row.name = payload.name.strip()
    row.category = payload.category.strip() or "General"
    row.monthly_amount = payload.monthly_amount
    row.sort_order = payload.sort_order
    row.is_active = payload.is_active
    db.commit()
    return {"ok": True}


@router.delete("/fixed-costs/{cost_id}")
def delete_fixed_cost(
    cost_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> dict:
    company_id = _require_company(current_user)
    row = db.get(AccountingFixedCost, cost_id)
    if not row or row.company_id != company_id:
        raise HTTPException(status_code=404, detail="Costo fijo no encontrado.")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ── Fixed Assets ──────────────────────────────────────────────────────────────

@router.get("/fixed-assets")
def list_fixed_assets(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
) -> list[dict]:
    company_id = _require_company(current_user)
    rows = list(db.scalars(
        select(AccountingFixedAsset)
        .where(AccountingFixedAsset.company_id == company_id)
        .where(AccountingFixedAsset.is_active.is_(True))
        .order_by(AccountingFixedAsset.acquisition_date.desc())
    ).all())
    return [
        {
            "id": r.id, "asset_name": r.asset_name, "category": r.category,
            "acquisition_date": str(r.acquisition_date),
            "acquisition_cost": str(r.acquisition_cost),
            "salvage_value": str(r.salvage_value),
            "useful_life_months": r.useful_life_months,
            "notes": r.notes,
        }
        for r in rows
    ]


@router.post("/fixed-assets")
def create_fixed_asset(
    payload: FixedAssetIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> dict:
    company_id = _require_company(current_user)
    if not payload.asset_name.strip():
        raise HTTPException(status_code=422, detail="El nombre del activo es requerido.")
    if payload.acquisition_cost <= 0:
        raise HTTPException(status_code=422, detail="El costo debe ser mayor a cero.")
    if payload.salvage_value < 0 or payload.salvage_value > payload.acquisition_cost:
        raise HTTPException(status_code=422, detail="El valor de rescate no puede ser mayor al costo.")
    row = AccountingFixedAsset(
        company_id=company_id,
        asset_name=payload.asset_name.strip(),
        category=payload.category.strip() or "Activo fijo",
        acquisition_date=payload.acquisition_date,
        acquisition_cost=payload.acquisition_cost,
        salvage_value=payload.salvage_value,
        useful_life_months=max(1, payload.useful_life_months),
        notes=payload.notes,
        created_by_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "asset_name": row.asset_name}


@router.delete("/fixed-assets/{asset_id}")
def deactivate_fixed_asset(
    asset_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> dict:
    company_id = _require_company(current_user)
    row = db.get(AccountingFixedAsset, asset_id)
    if not row or row.company_id != company_id:
        raise HTTPException(status_code=404, detail="Activo no encontrado.")
    row.is_active = False
    db.commit()
    return {"ok": True}


# ── Payables ──────────────────────────────────────────────────────────────────

@router.get("/payables")
def list_payables(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
) -> list[dict]:
    company_id = _require_company(current_user)
    rows = list(db.scalars(
        select(AccountingPayable)
        .where(AccountingPayable.company_id == company_id)
        .where(AccountingPayable.status.in_(["pending", "partial"]))
        .order_by(AccountingPayable.due_date.asc(), AccountingPayable.id.asc())
    ).all())
    return [
        {
            "id": r.id, "vendor_name": r.vendor_name, "concept": r.concept,
            "category": r.category,
            "due_date": str(r.due_date) if r.due_date else None,
            "amount": str(r.amount), "paid_amount": str(r.paid_amount),
            "status": r.status, "payment_method": r.payment_method, "notes": r.notes,
        }
        for r in rows
    ]


@router.post("/payables")
def create_payable(
    payload: PayableIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
) -> dict:
    company_id = _require_company(current_user)
    if not payload.vendor_name.strip() or not payload.concept.strip():
        raise HTTPException(status_code=422, detail="Proveedor y concepto son requeridos.")
    if payload.amount <= 0:
        raise HTTPException(status_code=422, detail="El monto debe ser mayor a cero.")
    row = AccountingPayable(
        company_id=company_id,
        vendor_name=payload.vendor_name.strip(),
        concept=payload.concept.strip(),
        category=payload.category.strip() or "General",
        due_date=payload.due_date,
        amount=payload.amount,
        notes=payload.notes,
        created_by_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "vendor_name": row.vendor_name, "amount": str(row.amount)}


@router.patch("/payables/{payable_id}")
def update_payable(
    payable_id: int,
    payload: PayableUpdateIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR))],
) -> dict:
    company_id = _require_company(current_user)
    row = db.get(AccountingPayable, payable_id)
    if not row or row.company_id != company_id:
        raise HTTPException(status_code=404, detail="Cuenta por pagar no encontrada.")
    if payload.status not in PAYABLE_STATUSES:
        raise HTTPException(status_code=422, detail="Estado inválido.")

    amount = float(row.amount)
    paid = max(0.0, min(float(payload.paid_amount), amount))

    if payload.status == "paid":
        paid = amount
    elif payload.status == "pending":
        paid = 0.0
    elif payload.status == "partial" and paid <= 0:
        raise HTTPException(status_code=422, detail="Captura un monto pagado para el estado 'parcial'.")

    row.paid_amount = Decimal(str(round(paid, 2)))
    row.status = payload.status
    row.payment_method = payload.payment_method
    row.notes = payload.notes
    if payload.status in ("paid", "partial"):
        row.paid_at = datetime.now(timezone.utc)

    db.commit()
    return {"ok": True, "status": row.status, "paid_amount": str(row.paid_amount)}


# ── Equity Movements ──────────────────────────────────────────────────────────

@router.get("/equity-movements")
def list_equity_movements(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> list[dict]:
    company_id = _require_company(current_user)
    rows = list(db.scalars(
        select(AccountingEquityMovement)
        .where(AccountingEquityMovement.company_id == company_id)
        .order_by(AccountingEquityMovement.movement_date.desc(), AccountingEquityMovement.id.desc())
    ).all())
    return [
        {
            "id": r.id, "movement_type": r.movement_type, "concept": r.concept,
            "amount": str(r.amount), "movement_date": str(r.movement_date), "notes": r.notes,
        }
        for r in rows
    ]


@router.post("/equity-movements")
def create_equity_movement(
    payload: EquityMovementIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> dict:
    company_id = _require_company(current_user)
    if payload.movement_type not in EQUITY_TYPES:
        raise HTTPException(status_code=422, detail="Tipo de movimiento inválido.")
    if not payload.concept.strip():
        raise HTTPException(status_code=422, detail="El concepto es requerido.")
    if payload.movement_type == "adjustment" and payload.amount == 0:
        raise HTTPException(status_code=422, detail="El ajuste no puede ser cero.")
    if payload.movement_type != "adjustment" and payload.amount <= 0:
        raise HTTPException(status_code=422, detail="El monto debe ser mayor a cero.")
    row = AccountingEquityMovement(
        company_id=company_id,
        movement_type=payload.movement_type,
        concept=payload.concept.strip(),
        amount=payload.amount,
        movement_date=payload.movement_date,
        notes=payload.notes,
        created_by_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "concept": row.concept, "amount": str(row.amount)}
