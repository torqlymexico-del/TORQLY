from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExternalSyncRecord


def upsert_external_sync_record(
    session: Session,
    *,
    provider: str,
    entity_type: str,
    entity_id: str | int,
    external_id: str,
    integration_account_id: int | None,
    sync_status: str,
    error_message: str | None = None,
) -> ExternalSyncRecord:
    record = session.scalar(
        select(ExternalSyncRecord)
        .where(ExternalSyncRecord.provider == provider)
        .where(ExternalSyncRecord.entity_type == entity_type)
        .where(ExternalSyncRecord.entity_id == str(entity_id))
    )
    if not record:
        record = ExternalSyncRecord(
            provider=provider,
            entity_type=entity_type,
            entity_id=str(entity_id),
            external_id=external_id,
            integration_account_id=integration_account_id,
        )
        session.add(record)

    record.external_id = external_id
    record.integration_account_id = integration_account_id
    record.sync_status = sync_status
    record.error_message = error_message
    record.last_synced_at = datetime.now(timezone.utc)
    session.flush()
    return record
