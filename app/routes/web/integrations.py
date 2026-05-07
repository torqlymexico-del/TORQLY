from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_company_id, require_roles
from app.enums import IntegrationAccountProvider, IntegrationAccountStatus, UserRole
from app.routes.web.common import base_context, redirect_with_message, templates
from app.services.integration_manager import (
    account_preview,
    create_integration_account,
    deactivate_integration_account,
    get_by_id,
    list_accounts,
    mark_default,
    test_connection,
    update_integration_account,
)
from app.services.exceptions import ServiceError


router = APIRouter(prefix="/settings/integrations", tags=["web-integrations"])

GOOGLE_PROVIDERS = {
    IntegrationAccountProvider.GOOGLE_CALENDAR.value,
    IntegrationAccountProvider.GOOGLE_SHEETS.value,
}
META_PROVIDERS = {
    IntegrationAccountProvider.WHATSAPP_META.value,
    IntegrationAccountProvider.META_BUSINESS.value,
}


def _group_filter(accounts: list, provider_group: str | None):
    if provider_group == "whatsapp":
        return [item for item in accounts if item.provider == IntegrationAccountProvider.WHATSAPP_META.value]
    if provider_group == "google":
        return [item for item in accounts if item.provider in GOOGLE_PROVIDERS]
    if provider_group == "clickup":
        return [item for item in accounts if item.provider == IntegrationAccountProvider.CLICKUP.value]
    if provider_group == "meta":
        return [item for item in accounts if item.provider in META_PROVIDERS]
    return accounts


def _integration_page(
    request: Request,
    db: Session,
    current_user,
    *,
    provider_group: str | None = None,
    edit: int | None = None,
):
    company_id = current_company_id(current_user)
    accounts = list_accounts(db, company_id=company_id, include_inactive=True) if company_id else []
    filtered_accounts = _group_filter(accounts, provider_group)
    selected = None
    if edit:
        try:
            selected = get_by_id(db, company_id, edit)
        except ServiceError:
            selected = None
    return templates.TemplateResponse(
        request,
        "integrations/index.html",
        base_context(
            request,
            current_user=current_user,
            accounts=filtered_accounts,
            account_previews=[account_preview(item) for item in filtered_accounts],
            selected=selected,
            selected_preview=account_preview(selected) if selected else None,
            provider_group=provider_group or "all",
            provider_values=[item.value for item in IntegrationAccountProvider],
            status_values=[item.value for item in IntegrationAccountStatus],
            page_title="Integraciones",
        ),
    )


@router.get("")
def integrations_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
    provider_group: str | None = Query(default=None),
    edit: int | None = Query(default=None),
):
    return _integration_page(request, db, current_user, provider_group=provider_group, edit=edit)


@router.get("/whatsapp")
def integrations_whatsapp(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
    edit: int | None = Query(default=None),
):
    return _integration_page(request, db, current_user, provider_group="whatsapp", edit=edit)


@router.get("/google")
def integrations_google(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
    edit: int | None = Query(default=None),
):
    return _integration_page(request, db, current_user, provider_group="google", edit=edit)


@router.get("/clickup")
def integrations_clickup(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
    edit: int | None = Query(default=None),
):
    return _integration_page(request, db, current_user, provider_group="clickup", edit=edit)


@router.get("/meta")
def integrations_meta(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
    edit: int | None = Query(default=None),
):
    return _integration_page(request, db, current_user, provider_group="meta", edit=edit)


def _form_payload(form) -> dict:
    return {
        "provider": form.get("provider"),
        "name": form.get("name"),
        "description": form.get("description"),
        "status": form.get("status") or IntegrationAccountStatus.ACTIVE.value,
        "is_default": form.get("is_default") in {"on", "true", "1", True},
        "access_token": form.get("access_token"),
        "verify_token": form.get("verify_token"),
        "webhook_secret": form.get("webhook_secret"),
        "phone_number_id": form.get("phone_number_id"),
        "business_account_id": form.get("business_account_id"),
        "api_version": form.get("api_version"),
        "auth_type": form.get("auth_type"),
        "credentials_json": form.get("credentials_json"),
        "client_id": form.get("client_id"),
        "client_secret": form.get("client_secret"),
        "refresh_token": form.get("refresh_token"),
        "calendar_id": form.get("calendar_id"),
        "spreadsheet_id": form.get("spreadsheet_id"),
        "token_uri": form.get("token_uri"),
        "api_token": form.get("api_token"),
        "team_id": form.get("team_id"),
        "space_id": form.get("space_id"),
        "folder_id": form.get("folder_id"),
        "list_id": form.get("list_id"),
        "business_id": form.get("business_id"),
        "app_id": form.get("app_id"),
        "ad_account_id": form.get("ad_account_id"),
        "page_id": form.get("page_id"),
        "instagram_business_id": form.get("instagram_business_id"),
        "secret_value": form.get("secret_value"),
        "custom_endpoint": form.get("custom_endpoint"),
    }


@router.post("")
async def integrations_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    company_id = current_company_id(current_user)
    try:
        form = await request.form()
        data = _form_payload(form)
        create_integration_account(
            db,
            company_id=company_id,
            provider=str(data.get("provider") or ""),
            data=data,
            actor=current_user,
        )
        db.commit()
        return redirect_with_message("/settings/integrations", "Integracion creada correctamente.")
    except ServiceError as exc:
        db.rollback()
        return redirect_with_message("/settings/integrations", str(exc), "error")


@router.post("/{integration_id}/edit")
async def integrations_update(
    integration_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    company_id = current_company_id(current_user)
    try:
        form = await request.form()
        update_integration_account(
            db,
            company_id=company_id,
            integration_id=integration_id,
            data=_form_payload(form),
            actor=current_user,
        )
        db.commit()
        return redirect_with_message("/settings/integrations", "Integracion actualizada.")
    except ServiceError as exc:
        db.rollback()
        return redirect_with_message(f"/settings/integrations?edit={integration_id}", str(exc), "error")


@router.post("/{integration_id}/test")
def integrations_test(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    company_id = current_company_id(current_user)
    try:
        result = test_connection(db, integration_id, company_id=company_id, actor=current_user)
        db.commit()
        level = "success" if result.get("ok") else "error"
        return redirect_with_message("/settings/integrations", result.get("message"), level)
    except ServiceError as exc:
        db.rollback()
        return redirect_with_message("/settings/integrations", str(exc), "error")


@router.post("/{integration_id}/default")
def integrations_default(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    company_id = current_company_id(current_user)
    try:
        account = get_by_id(db, company_id, integration_id)
        mark_default(db, company_id, account.provider, integration_id, actor=current_user)
        db.commit()
        return redirect_with_message("/settings/integrations", "Integracion marcada como default.")
    except ServiceError as exc:
        db.rollback()
        return redirect_with_message("/settings/integrations", str(exc), "error")


@router.post("/{integration_id}/toggle")
def integrations_toggle(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    company_id = current_company_id(current_user)
    try:
        account = get_by_id(db, company_id, integration_id)
        if account.status == IntegrationAccountStatus.INACTIVE.value:
            update_integration_account(
                db,
                company_id=company_id,
                integration_id=integration_id,
                data={"status": IntegrationAccountStatus.ACTIVE.value},
                actor=current_user,
            )
            message = "Integracion activada."
        else:
            deactivate_integration_account(
                db,
                company_id=company_id,
                integration_id=integration_id,
                actor=current_user,
            )
            message = "Integracion desactivada."
        db.commit()
        return redirect_with_message("/settings/integrations", message)
    except ServiceError as exc:
        db.rollback()
        return redirect_with_message("/settings/integrations", str(exc), "error")


@router.post("/{integration_id}/disconnect")
def integrations_disconnect(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    company_id = current_company_id(current_user)
    try:
        deactivate_integration_account(
            db,
            company_id=company_id,
            integration_id=integration_id,
            actor=current_user,
        )
        db.commit()
        return redirect_with_message("/settings/integrations", "Integracion desconectada de forma segura.")
    except ServiceError as exc:
        db.rollback()
        return redirect_with_message("/settings/integrations", str(exc), "error")
