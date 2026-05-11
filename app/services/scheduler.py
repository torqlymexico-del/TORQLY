from __future__ import annotations

from datetime import datetime

from app.config import settings
from app.database import SessionLocal
from app.services.automations import (
    run_daily_close_automation,
    run_low_stock_monitor,
    run_upcoming_appointment_automations,
)
from app.services.whatsapp_conversations import send_reengagement_messages
from app.utils.dates import get_timezone
from app.utils.logger import get_logger


logger = get_logger(__name__)
_scheduler = None


def _daily_close_parts() -> tuple[int, int]:
    try:
        hour_str, minute_str = settings.daily_close_time.split(":", 1)
        return int(hour_str), int(minute_str)
    except Exception:
        logger.warning("DAILY_CLOSE_TIME invalido: %s. Se usara 20:00.", settings.daily_close_time)
        return 20, 0


def _run_job(job_name: str, callback) -> None:
    with SessionLocal() as session:
        try:
            result = callback(session)
            logger.info("Scheduler %s ejecutado: %s", job_name, result)
        except Exception as exc:  # pragma: no cover - defensive scheduler branch
            session.rollback()
            logger.exception("Scheduler %s fallo: %s", job_name, exc)


def start_scheduler() -> dict:
    global _scheduler

    if not settings.scheduler_enabled:
        logger.info("Scheduler desactivado por configuracion.")
        return {"started": False, "reason": "disabled"}

    if _scheduler is not None and getattr(_scheduler, "running", False):
        return {"started": True, "reason": "already_running"}

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning("APScheduler no esta instalado. El scheduler no se iniciara.")
        return {"started": False, "reason": "missing_dependency"}

    timezone = get_timezone()
    hour, minute = _daily_close_parts()
    scheduler = BackgroundScheduler(timezone=timezone)
    scheduler.add_job(
        lambda: _run_job("upcoming_appointments", run_upcoming_appointment_automations),
        trigger="interval",
        minutes=5,
        id="torqly_upcoming_appointments",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        lambda: _run_job("low_stock", run_low_stock_monitor),
        trigger="interval",
        minutes=30,
        id="torqly_low_stock",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        lambda: _run_job("daily_close", run_daily_close_automation),
        trigger="cron",
        hour=hour,
        minute=minute,
        id="torqly_daily_close",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        lambda: _run_job("whatsapp_reengagement", send_reengagement_messages),
        trigger="cron",
        hour=10,
        minute=0,
        id="torqly_whatsapp_reengagement",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduler iniciado a las %s", datetime.now(timezone).isoformat())
    return {"started": True, "reason": "ok"}


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
