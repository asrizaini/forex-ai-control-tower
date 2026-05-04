from __future__ import annotations

import os
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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
    return f"{to_local(value).strftime('%Y-%m-%d %H:%M:%S')} {app_timezone_name()}"
