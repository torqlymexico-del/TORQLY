from datetime import date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings


def get_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(settings.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def local_now() -> datetime:
    return datetime.now(get_timezone())


def combine_local_date_time(value_date: date, value_time: time) -> datetime:
    naive_value = datetime.combine(value_date, value_time)
    return naive_value.replace(tzinfo=get_timezone())
