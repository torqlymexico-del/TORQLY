"""Meta Business API — Ads Leads y Campañas."""
from __future__ import annotations

import httpx

from app.enums import IntegrationAccountProvider, IntegrationStatus
from app.services.audit import log_integration_event
from app.services.integration_manager import (
    handle_expired_credentials,
    log_usage,
    resolve_provider_account,
)

GRAPH_API_URL = "https://graph.facebook.com"
DEFAULT_API_VERSION = "v20.0"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _runtime(session, company_id: int | None, account_id: int | None) -> dict:
    return resolve_provider_account(
        session,
        company_id=company_id,
        provider=IntegrationAccountProvider.META_BUSINESS.value,
        selected_id=account_id,
    )


def _base_url(runtime: dict) -> str:
    version = runtime.get("config", {}).get("api_version") or DEFAULT_API_VERSION
    return f"{GRAPH_API_URL}/{version}"


def _token(runtime: dict) -> str:
    return runtime.get("credentials", {}).get("access_token", "")


def _log(session, runtime: dict, event_type: str, status: str, error: str | None = None, payload: dict | None = None):
    account = runtime.get("integration_account")
    log_integration_event(
        session,
        provider=IntegrationAccountProvider.META_BUSINESS.value,
        integration_account_id=account.id if account else None,
        event_type=event_type,
        status=status,
        entity_type="meta_business",
        entity_id=None,
        request_payload=payload or {},
        error_message=error,
    )


# ── Leads ─────────────────────────────────────────────────────────────────────

def get_leads(
    session,
    *,
    company_id: int | None = None,
    integration_account_id: int | None = None,
    form_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    Obtiene leads del Ad Account o de un formulario específico.
    Si form_id está dado, usa /{form_id}/leads; si no, usa /{ad_account_id}/leads.
    """
    runtime = _runtime(session, company_id, integration_account_id)
    if runtime.get("source") == "none":
        return []

    token = _token(runtime)
    config = runtime.get("config", {})
    ad_account_id = config.get("ad_account_id") or ""

    if not token or (not form_id and not ad_account_id):
        return []

    endpoint_id = form_id if form_id else ad_account_id
    url = f"{_base_url(runtime)}/{endpoint_id}/leads"

    try:
        resp = httpx.get(
            url,
            params={
                "access_token": token,
                "fields": "id,created_time,field_data,ad_id,ad_name,adset_name,campaign_id,campaign_name,form_id",
                "limit": limit,
            },
            timeout=20,
        )
        if resp.status_code == 401:
            handle_expired_credentials(session, runtime.get("integration_account"))
        resp.raise_for_status()
        log_usage(session, runtime.get("integration_account"))
        raw_leads = resp.json().get("data", [])
        _log(session, runtime, "meta.leads.fetch", IntegrationStatus.SUCCESS.value)
        return [_parse_lead(lead) for lead in raw_leads]
    except Exception as exc:
        _log(session, runtime, "meta.leads.fetch", IntegrationStatus.FAILED.value, error=str(exc))
        raise


def get_lead_forms(
    session,
    *,
    company_id: int | None = None,
    integration_account_id: int | None = None,
) -> list[dict]:
    """Lista los formularios de leads de la página de Facebook."""
    runtime = _runtime(session, company_id, integration_account_id)
    if runtime.get("source") == "none":
        return []

    token = _token(runtime)
    page_id = runtime.get("config", {}).get("page_id") or ""
    if not token or not page_id:
        return []

    try:
        resp = httpx.get(
            f"{_base_url(runtime)}/{page_id}/leadgen_forms",
            params={
                "access_token": token,
                "fields": "id,name,status,leads_count,created_time",
                "limit": 50,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception:
        return []


# ── Campañas ──────────────────────────────────────────────────────────────────

def get_campaigns(
    session,
    *,
    company_id: int | None = None,
    integration_account_id: int | None = None,
    date_preset: str = "last_30d",
) -> list[dict]:
    """
    Lista campañas del Ad Account con métricas de los últimos 30 días.
    date_preset: last_7d | last_30d | last_90d | this_month | last_month
    """
    runtime = _runtime(session, company_id, integration_account_id)
    if runtime.get("source") == "none":
        return []

    token = _token(runtime)
    ad_account_id = runtime.get("config", {}).get("ad_account_id") or ""
    if not token or not ad_account_id:
        return []

    try:
        resp = httpx.get(
            f"{_base_url(runtime)}/{ad_account_id}/campaigns",
            params={
                "access_token": token,
                "fields": "id,name,status,objective,daily_budget,lifetime_budget,created_time,start_time",
                "limit": 50,
            },
            timeout=15,
        )
        resp.raise_for_status()
        campaigns = resp.json().get("data", [])

        enriched = []
        for camp in campaigns:
            insights = _get_campaign_insights(camp["id"], token, _base_url(runtime), date_preset)
            enriched.append({
                "id": camp["id"],
                "name": camp["name"],
                "status": camp.get("status", ""),
                "objective": camp.get("objective", ""),
                "daily_budget": _format_budget(camp.get("daily_budget")),
                "lifetime_budget": _format_budget(camp.get("lifetime_budget")),
                "start_time": camp.get("start_time", ""),
                "spend": insights.get("spend", "0"),
                "impressions": insights.get("impressions", "0"),
                "clicks": insights.get("clicks", "0"),
                "leads": insights.get("leads", "0"),
                "cpl": insights.get("cpl", None),
            })

        log_usage(session, runtime.get("integration_account"))
        _log(session, runtime, "meta.campaigns.fetch", IntegrationStatus.SUCCESS.value)
        return enriched
    except Exception as exc:
        _log(session, runtime, "meta.campaigns.fetch", IntegrationStatus.FAILED.value, error=str(exc))
        raise


def _get_campaign_insights(campaign_id: str, token: str, base_url: str, date_preset: str) -> dict:
    try:
        resp = httpx.get(
            f"{base_url}/{campaign_id}/insights",
            params={
                "access_token": token,
                "fields": "spend,impressions,clicks,actions",
                "date_preset": date_preset,
                "limit": 1,
            },
            timeout=10,
        )
        if not resp.is_success:
            return {}
        data = resp.json().get("data", [{}])
        if not data:
            return {}
        row = data[0]
        lead_action = next(
            (a["value"] for a in row.get("actions", []) if a["action_type"] == "lead"), "0"
        )
        spend = float(row.get("spend", 0) or 0)
        leads = int(lead_action or 0)
        cpl = round(spend / leads, 2) if leads > 0 else None
        return {
            "spend": row.get("spend", "0"),
            "impressions": row.get("impressions", "0"),
            "clicks": row.get("clicks", "0"),
            "leads": str(leads),
            "cpl": str(cpl) if cpl is not None else None,
        }
    except Exception:
        return {}


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_lead(raw: dict) -> dict:
    fields = {f["name"]: (f.get("values") or [""])[0] for f in raw.get("field_data", [])}
    return {
        "id": raw.get("id", ""),
        "created_time": raw.get("created_time", ""),
        "ad_name": raw.get("ad_name", ""),
        "adset_name": raw.get("adset_name", ""),
        "campaign_name": raw.get("campaign_name", ""),
        "form_id": raw.get("form_id", ""),
        "name": fields.get("full_name") or fields.get("first_name", ""),
        "email": fields.get("email", ""),
        "phone": fields.get("phone_number") or fields.get("phone", ""),
        "raw_fields": fields,
    }


def _format_budget(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return f"${float(value) / 100:,.2f}"
    except (ValueError, TypeError):
        return str(value)
