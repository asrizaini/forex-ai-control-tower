from __future__ import annotations

import os
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def utcnow() -> datetime:
    """Return the current UTC datetime as a naive object.

    Uses datetime.now(UTC) internally (avoiding the deprecated datetime.utcnow())
    but strips timezone info for SQLAlchemy DateTime column compatibility,
    which stores naive datetimes by default.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def app_timezone_name() -> str:
    return os.getenv("APP_TIMEZONE") or os.getenv("TZ") or "Asia/Kuala_Lumpur"


def app_timezone() -> ZoneInfo:
    timezone_name = app_timezone_name()
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("Asia/Kuala_Lumpur")


def local_now() -> datetime:
    return datetime.now(app_timezone())


def to_local(value: datetime | None = None) -> datetime:
    source = value or datetime.now(UTC)
    if source.tzinfo is None:
        source = source.replace(tzinfo=UTC)
    return source.astimezone(app_timezone())


def iso_local(value: datetime | None = None) -> str:
    return to_local(value).isoformat(timespec="seconds")


def format_local(value: datetime | None = None) -> str:
    local = to_local(value)
    return f"{local.strftime('%Y-%m-%d %I:%M:%S %p')} GMT+8"
