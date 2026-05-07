from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.enums import IntegrationAccountProvider, IntegrationStatus
from app.integrations.google.auth import (
    load_google_credentials_from_runtime,
    load_google_sheets_credentials,
)
from app.models import Appointment, InventoryProduct
from app.services.audit import log_integration_event
from app.services.integration_manager import (
    handle_expired_credentials,
    log_usage,
    resolve_provider_account,
)
from app.services.cash_cuts import calculate_cash_cut_summary
from app.services.reports import commissions_report, sales_report


SHEET_TABS = {
    "daily_cut": "Daily Cut",
    "sales": "Daily Sales",
    "commissions": "Commissions",
    "inventory": "Inventory",
    "agenda": "Agenda",
}


def _get_sheets_service(session, *, company_id: int | None = None, integration_account_id: int | None = None):
    runtime = resolve_provider_account(
        session,
        company_id=company_id,
        provider=IntegrationAccountProvider.GOOGLE_SHEETS.value,
        selected_id=integration_account_id,
    )
    account = runtime.get("integration_account")
    if runtime.get("source") == "database":
        credentials, error = load_google_credentials_from_runtime(
            credentials=runtime.get("credentials") or {},
            config=runtime.get("config") or {},
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
    elif runtime.get("source") == "settings":
        credentials, error = load_google_sheets_credentials()
    else:
        credentials, error = None, "Google Sheets esta desactivado o sin credenciales."
    if error:
        return None, error, runtime
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return None, "Las dependencias de Google no estan instaladas.", runtime
    if account:
        log_usage(session, account.id)
    return build("sheets", "v4", credentials=credentials, cache_discovery=False), None, runtime


def _ensure_sheet(service, spreadsheet_id: str, title: str) -> None:
    metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_titles = {sheet["properties"]["title"] for sheet in metadata.get("sheets", [])}
    if title in existing_titles:
        return
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
    ).execute()


def _write_rows(service, *, spreadsheet_id: str, title: str, rows: list[list[str]]) -> None:
    _ensure_sheet(service, spreadsheet_id, title)
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"'{title}'!A1:Z2000",
        body={},
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{title}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": rows},
    ).execute()


def _export(
    session,
    *,
    company_id: int | None,
    integration_account_id: int | None,
    sheet_key: str,
    entity_type: str,
    entity_id: str | int | None,
    event_type: str,
    rows: list[list[str]],
):
    service, error, runtime = _get_sheets_service(
        session,
        company_id=company_id,
        integration_account_id=integration_account_id,
    )
    account = runtime.get("integration_account")
    config = runtime.get("config") or {}
    sheet_title = SHEET_TABS[sheet_key]
    spreadsheet_id = config.get("spreadsheet_id")
    if not spreadsheet_id and runtime.get("source") == "settings":
        from app.config import settings

        spreadsheet_id = settings.google_sheets_spreadsheet_id
    if error or not spreadsheet_id:
        message = error or "Falta spreadsheet_id para Google Sheets."
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_SHEETS.value,
            integration_account_id=account.id if account else None,
            event_type=event_type,
            status=IntegrationStatus.SKIPPED.value,
            entity_type=entity_type,
            entity_id=entity_id,
            request_payload={"sheet_title": sheet_title, "rows": len(rows)},
            error_message=message,
        )
        session.commit()
        return {"status": "skipped", "message": message, "sheet_title": sheet_title}

    try:
        _write_rows(service, spreadsheet_id=spreadsheet_id, title=sheet_title, rows=rows)
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_SHEETS.value,
            integration_account_id=account.id if account else None,
            event_type=event_type,
            status=IntegrationStatus.SUCCESS.value,
            entity_type=entity_type,
            entity_id=entity_id,
            request_payload={"sheet_title": sheet_title, "rows": len(rows)},
            response_payload={"spreadsheet_id": spreadsheet_id},
        )
        session.commit()
        return {
            "status": "success",
            "sheet_title": sheet_title,
            "spreadsheet_id": spreadsheet_id,
            "rows": len(rows),
            "integration_account_id": account.id if account else None,
        }
    except Exception as exc:  # pragma: no cover - external API branch
        if account and "401" in str(exc):
            handle_expired_credentials(session, account.id, error_message=str(exc))
        log_integration_event(
            session,
            provider=IntegrationAccountProvider.GOOGLE_SHEETS.value,
            integration_account_id=account.id if account else None,
            event_type=event_type,
            status=IntegrationStatus.FAILED.value,
            entity_type=entity_type,
            entity_id=entity_id,
            request_payload={"sheet_title": sheet_title, "rows": len(rows)},
            error_message=str(exc),
        )
        session.commit()
        return {"status": "error", "message": str(exc), "sheet_title": sheet_title}


def export_daily_cut(
    session,
    *,
    target_date: date | None = None,
    company_id: int | None = None,
    integration_account_id: int | None = None,
) -> dict:
    report_date = target_date or date.today()
    summary = calculate_cash_cut_summary(session, target_date=report_date)
    rows = [
        ["Fecha", "Ventas", "Efectivo", "Tarjeta", "Transferencia", "Cortesias", "Descuentos", "Comisiones", "Costo", "Utilidad", "Servicios cobrados", "Servicios cancelados"],
        [
            report_date.isoformat(),
            str(summary["total_sales"]),
            str(summary["cash_total"]),
            str(summary["card_total"]),
            str(summary["transfer_total"]),
            str(summary["courtesy_total"]),
            str(summary["discounts_total"]),
            str(summary["commissions_total"]),
            str(summary["cost_total"]),
            str(summary["estimated_profit"]),
            str(summary["services_charged"]),
            str(summary["services_canceled"]),
        ],
    ]
    return _export(
        session,
        company_id=company_id,
        integration_account_id=integration_account_id,
        sheet_key="daily_cut",
        entity_type="cash_cut",
        entity_id=report_date.isoformat(),
        event_type="cash_cut.export",
        rows=rows,
    )


def export_daily_sales(
    session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    company_id: int | None = None,
    integration_account_id: int | None = None,
) -> dict:
    report = sales_report(session, date_from=date_from, date_to=date_to)
    rows = [["Ventas por dia"], ["Fecha", "Ventas", "Transacciones", "Ticket promedio"]]
    rows.extend(
        [[item["date"], str(item["total_sales"]), str(item["transactions"]), str(item["average_ticket"])] for item in report["sales_by_day"]]
    )
    rows.extend([[], ["Ventas por metodo"], ["Metodo", "Ventas"]])
    rows.extend([[item["payment_method"], str(item["total_sales"])] for item in report["sales_by_payment_method"]])
    return _export(
        session,
        company_id=company_id,
        integration_account_id=integration_account_id,
        sheet_key="sales",
        entity_type="report",
        entity_id=f"{report['date_from']}:{report['date_to']}",
        event_type="sales.export",
        rows=rows,
    )


def export_commissions(
    session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    company_id: int | None = None,
    integration_account_id: int | None = None,
) -> dict:
    report = commissions_report(session, date_from=date_from, date_to=date_to)
    rows = [["Comisiones por operador"], ["Operador", "Registros", "Base", "Extras", "Total"]]
    rows.extend(
        [
            [item["operator_name"], str(item["commissions_count"]), str(item["base_amount"]), str(item["extra_amount"]), str(item["total_amount"])]
            for item in report["by_operator"]
        ]
    )
    rows.extend([[], ["Comisiones por dia"], ["Fecha", "Total"]])
    rows.extend([[item["date"], str(item["total_amount"])] for item in report["by_day"]])
    return _export(
        session,
        company_id=company_id,
        integration_account_id=integration_account_id,
        sheet_key="commissions",
        entity_type="report",
        entity_id=f"{report['date_from']}:{report['date_to']}",
        event_type="commissions.export",
        rows=rows,
    )


def export_inventory(
    session,
    *,
    company_id: int | None = None,
    integration_account_id: int | None = None,
) -> dict:
    products = list(
        session.scalars(
            select(InventoryProduct)
            .where(InventoryProduct.deleted_at.is_(None))
            .order_by(InventoryProduct.name.asc())
        ).all()
    )
    rows = [["Producto", "Categoria", "Stock", "Unidad", "Costo", "Minimo", "Activo"]]
    rows.extend(
        [
            [product.name, product.category or "", str(product.stock), product.unit, str(product.cost), str(product.minimum_stock), "si" if product.is_active else "no"]
            for product in products
        ]
    )
    return _export(
        session,
        company_id=company_id,
        integration_account_id=integration_account_id,
        sheet_key="inventory",
        entity_type="inventory",
        entity_id="inventory",
        event_type="inventory.export",
        rows=rows,
    )


def export_agenda(
    session,
    *,
    target_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    company_id: int | None = None,
    integration_account_id: int | None = None,
) -> dict:
    start_date = target_date or date_from or date.today()
    end_date = target_date or date_to or start_date
    appointments = list(
        session.scalars(
            select(Appointment)
            .options(
                joinedload(Appointment.client),
                joinedload(Appointment.vehicle),
                joinedload(Appointment.service),
                joinedload(Appointment.operator),
            )
            .where(Appointment.deleted_at.is_(None))
            .where(func.date(Appointment.scheduled_start) >= start_date)
            .where(func.date(Appointment.scheduled_start) <= end_date)
            .order_by(Appointment.scheduled_start.asc(), Appointment.id.asc())
        ).unique().all()
    )
    rows = [["ID", "Fecha", "Hora", "Cliente", "Vehiculo", "Servicio", "Operador", "Estado", "Cobro"]]
    rows.extend(
        [
            [
                str(appointment.id),
                appointment.scheduled_start.date().isoformat(),
                appointment.scheduled_start.strftime("%H:%M"),
                appointment.client.name if appointment.client else "",
                f"{appointment.vehicle.brand} {appointment.vehicle.model}" if appointment.vehicle else "",
                appointment.service.name if appointment.service else "",
                appointment.operator.name if appointment.operator else "",
                appointment.status,
                appointment.charge_status,
            ]
            for appointment in appointments
        ]
    )
    return _export(
        session,
        company_id=company_id,
        integration_account_id=integration_account_id,
        sheet_key="agenda",
        entity_type="agenda",
        entity_id=f"{start_date}:{end_date}",
        event_type="agenda.export",
        rows=rows,
    )
