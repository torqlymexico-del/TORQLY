from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import IntegrationStatus, UserRole
from app.models import AuditLog, IntegrationAccount, IntegrationLog, User
from app.routes.web.common import base_context, templates
from app.services.integration_manager import account_preview, list_accounts


router = APIRouter(prefix="/admin", tags=["web-admin"])


def _database_status(db: Session) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Conexion activa"}
    except Exception as exc:  # pragma: no cover - defensive branch
        return {"status": "error", "message": str(exc)}


@router.get("/health")
def admin_health_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    company_id = current_company_id(current_user)
    accounts = list_accounts(db, company_id=company_id, include_inactive=True) if company_id else []
    integration_accounts = [account_preview(account) for account in accounts]
    latest_success = {}
    for provider in sorted({item.provider for item in accounts}):
        latest_success[provider] = db.scalar(
            select(IntegrationLog)
            .where(IntegrationLog.provider == provider)
            .where(IntegrationLog.status == IntegrationStatus.SUCCESS.value)
            .order_by(IntegrationLog.created_at.desc(), IntegrationLog.id.desc())
        )
    return templates.TemplateResponse(
        request,
        "admin/health.html",
        base_context(
            request,
            current_user=current_user,
            db_status=_database_status(db),
            system_version="0.1.0",
            integration_accounts=integration_accounts,
            latest_success=latest_success,
            scheduler_enabled=settings.scheduler_enabled,
            daily_close_time=settings.daily_close_time,
            page_title="Salud del sistema",
        ),
    )


@router.get("/logs")
def admin_logs_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
    action: str | None = Query(default=None),
    actor_id: int | None = Query(default=None),
    limit: int = Query(default=150, ge=20, le=500),
):
    company_id = current_company_id(current_user)
    company_user_ids = select(User.id).where(User.company_id == company_id) if company_id is not None else None
    query = (
        select(AuditLog)
        .options(joinedload(AuditLog.actor_user))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    if company_user_ids is not None:
        query = query.where(
            (AuditLog.actor_user_id.is_(None)) | (AuditLog.actor_user_id.in_(company_user_ids))
        )
    if action:
        query = query.where(AuditLog.action == action)
    if actor_id:
        query = query.where(AuditLog.actor_user_id == actor_id)
    logs = list(db.scalars(query).all())
    actors = list(db.scalars(select(User).where(User.company_id == company_id).order_by(User.name.asc())).all())
    return templates.TemplateResponse(
        request,
        "admin/logs.html",
        base_context(
            request,
            current_user=current_user,
            logs=logs,
            actors=actors,
            filters={"action": action or "", "actor_id": actor_id, "limit": limit},
            page_title="Auditoria",
        ),
    )


@router.get("/integration-logs")
def admin_integration_logs_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
    provider: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=150, ge=20, le=500),
):
    company_id = current_company_id(current_user)
    company_accounts = list_accounts(db, company_id=company_id, include_inactive=True) if company_id else []
    company_account_ids = [account.id for account in company_accounts]
    query = (
        select(IntegrationLog)
        .options(joinedload(IntegrationLog.integration_account))
        .order_by(IntegrationLog.created_at.desc(), IntegrationLog.id.desc())
        .limit(limit)
    )
    if company_account_ids:
        query = query.where(
            (IntegrationLog.integration_account_id.is_(None))
            | (IntegrationLog.integration_account_id.in_(company_account_ids))
        )
    if provider:
        query = query.where(IntegrationLog.provider == provider)
    if status:
        query = query.where(IntegrationLog.status == status)
    logs = list(db.scalars(query).all())
    return templates.TemplateResponse(
        request,
        "admin/integration_logs.html",
        base_context(
            request,
            current_user=current_user,
            logs=logs,
            providers=sorted({item.provider for item in company_accounts} | {item.provider for item in logs}),
            status_values=[item.value for item in IntegrationStatus],
            filters={"provider": provider or "", "status": status or "", "limit": limit},
            page_title="Logs de integracion",
        ),
    )
