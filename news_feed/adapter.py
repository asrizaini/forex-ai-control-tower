from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


HIGH_IMPACT_LEVELS = {"high", "red", "critical", "3"}
MEDIUM_IMPACT_LEVELS = {"medium", "orange", "moderate", "2"}
LOW_IMPACT_LEVELS = {"low", "yellow", "minor", "1"}
HIGH_IMPACT_KEYWORDS = (
    "cpi",
    "consumer price",
    "inflation",
    "interest rate",
    "rate decision",
    "fomc",
    "nonfarm",
    "nfp",
    "payroll",
    "unemployment",
    "gdp",
    "retail sales",
    "pce",
    "ppi",
    "central bank",
    "ecb",
    "boe",
    "boj",
    "fed",
)
CURRENCY_BY_SYMBOL = {
    "EURUSD": {"EUR", "USD"},
    "GBPUSD": {"GBP", "USD"},
    "USDJPY": {"USD", "JPY"},
    "XAUUSD": {"XAU", "USD"},
    "AUDUSD": {"AUD", "USD"},
    "USDCAD": {"USD", "CAD"},
    "USDCHF": {"USD", "CHF"},
    "NZDUSD": {"NZD", "USD"},
}
COUNTRY_TO_CURRENCY = {
    "australia": "AUD",
    "canada": "CAD",
    "china": "CNY",
    "euro area": "EUR",
    "eurozone": "EUR",
    "france": "EUR",
    "germany": "EUR",
    "italy": "EUR",
    "japan": "JPY",
    "new zealand": "NZD",
    "switzerland": "CHF",
    "united kingdom": "GBP",
    "uk": "GBP",
    "united states": "USD",
    "us": "USD",
    "usa": "USD",
}


@dataclass(frozen=True)
class NewsEvent:
    title: str
    event_time: datetime
    impact: str
    currencies: tuple[str, ...]
    source: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_time"] = self.event_time.isoformat().replace("+00:00", "Z")
        return payload


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _event_currencies(raw: dict[str, Any]) -> tuple[str, ...]:
    values = raw.get("currencies", raw.get("currency", []))
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return ()
    return tuple(sorted({str(item).upper().strip() for item in values if str(item).strip()}))


def _impact_level(raw: dict[str, Any], title: str) -> str:
    values = (
        raw.get("impact"),
        raw.get("importance"),
        raw.get("volatility"),
        raw.get("priority"),
        raw.get("level"),
    )
    for value in values:
        normalized = str(value).lower().strip()
        if normalized in HIGH_IMPACT_LEVELS:
            return "high"
        if normalized in MEDIUM_IMPACT_LEVELS:
            return "medium"
        if normalized in LOW_IMPACT_LEVELS:
            return "low"
    lowered_title = title.lower()
    if any(keyword in lowered_title for keyword in HIGH_IMPACT_KEYWORDS):
        return "high"
    return "unknown"


def _normalise_events(data: Any, source: str) -> list[NewsEvent]:
    if isinstance(data, dict):
        raw_events = data.get("events", [])
    elif isinstance(data, list):
        raw_events = data
    else:
        raw_events = []
    events: list[NewsEvent] = []
    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        event_time = _parse_time(raw.get("event_time", raw.get("time", raw.get("timestamp"))))
        if not event_time:
            continue
        currencies = _event_currencies(raw)
        if not currencies:
            continue
        events.append(
            NewsEvent(
                title=str(raw.get("title", raw.get("name", "Economic event")))[:240],
                event_time=event_time,
                impact=_impact_level(raw, str(raw.get("title", raw.get("name", "")))),
                currencies=currencies,
                source=str(raw.get("source", source))[:120],
            )
        )
    return sorted(events, key=lambda item: item.event_time)


def _normalise_fmp_events(data: Any) -> list[NewsEvent]:
    if not isinstance(data, list):
        return []
    events: list[NewsEvent] = []
    for raw in data:
        if not isinstance(raw, dict):
            continue
        event_time = _parse_time(raw.get("date", raw.get("event_time", raw.get("time"))))
        if not event_time:
            continue
        title = str(raw.get("event", raw.get("title", raw.get("name", "Economic event"))))[:240]
        currency = str(raw.get("currency", "")).upper().strip()
        if not currency:
            country = str(raw.get("country", "")).lower().strip()
            currency = COUNTRY_TO_CURRENCY.get(country, "")
        currencies = (currency,) if currency else ()
        if not currencies:
            continue
        events.append(
            NewsEvent(
                title=title,
                event_time=event_time,
                impact=_impact_level(raw, title),
                currencies=currencies,
                source="financial_modeling_prep",
            )
        )
    return sorted(events, key=lambda item: item.event_time)


def _load_file(path: str) -> tuple[list[NewsEvent], str | None]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], type(exc).__name__
    return _normalise_events(data, "file"), None


def _read_json_url(url: str, headers: dict[str, str]) -> tuple[Any, str | None]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8")), None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return None, type(exc).__name__


def _load_url(url: str, api_key: str | None) -> tuple[list[NewsEvent], str | None]:
    if not url.lower().startswith("https://"):
        return [], "NEWS_CALENDAR_URL must use https"
    headers = {"Accept": "application/json", "User-Agent": "forex-ai-control-tower/0.1"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data, error = _read_json_url(url, headers)
    if error:
        return [], error
    return _normalise_events(data, "https"), None


def _load_fmp(api_key: str | None) -> tuple[list[NewsEvent], str | None]:
    if not api_key:
        return [], "NEWS_PROVIDER_API_KEY is not configured"
    today = _utcnow().date()
    start_date = os.getenv("NEWS_CALENDAR_FROM", today.isoformat())
    end_date = os.getenv("NEWS_CALENDAR_TO", (today + timedelta(days=7)).isoformat())
    query = urlencode({"from": start_date, "to": end_date, "apikey": api_key})
    url = f"https://financialmodelingprep.com/stable/economic-calendar?{query}"
    headers = {"Accept": "application/json", "User-Agent": "forex-ai-control-tower/0.1"}
    data, error = _read_json_url(url, headers)
    if error:
        return [], error
    return _normalise_fmp_events(data), None


def _currencies_for_symbol(symbol: str | None) -> set[str]:
    if not symbol:
        return set()
    normalized = symbol.upper().strip()
    if normalized in CURRENCY_BY_SYMBOL:
        return set(CURRENCY_BY_SYMBOL[normalized])
    if len(normalized) >= 6:
        return {normalized[:3], normalized[3:6]}
    return set()


def _load_provider_events() -> tuple[str, list[NewsEvent], str | None]:
    provider_type = os.getenv("NEWS_PROVIDER_TYPE", "disabled").lower().strip()
    if os.getenv("NEWS_PROVIDER_ENABLED", "false").lower() != "true":
        return provider_type, [], "NEWS_PROVIDER_ENABLED is false"
    if provider_type in {"manual_json", "file"}:
        path = os.getenv("NEWS_CALENDAR_FILE", "")
        if not path:
            return provider_type, [], "NEWS_CALENDAR_FILE is not configured"
        events, error = _load_file(path)
        return provider_type, events, error
    if provider_type in {"http_json", "https_json"}:
        url = os.getenv("NEWS_CALENDAR_URL", "")
        if not url:
            return provider_type, [], "NEWS_CALENDAR_URL is not configured"
        events, error = _load_url(url, os.getenv("NEWS_PROVIDER_API_KEY"))
        return provider_type, events, error
    if provider_type in {"fmp", "fmp_economic_calendar", "financial_modeling_prep"}:
        events, error = _load_fmp(os.getenv("NEWS_PROVIDER_API_KEY"))
        return provider_type, events, error
    if provider_type == "env_window":
        minutes = int(os.getenv("NEWS_HIGH_IMPACT_NEXT_MINUTES", "999"))
        event_time = _utcnow() + timedelta(minutes=minutes)
        return provider_type, [NewsEvent("Environment high-impact window", event_time, "high", ("EUR", "USD"), "env")], None
    return provider_type, [], f"Unsupported NEWS_PROVIDER_TYPE: {provider_type}"


def evaluate_news_status(symbol: str | None = None) -> dict[str, Any]:
    provider_type, events, error = _load_provider_events()
    now = _utcnow()
    high_impact_window = int(os.getenv("NEWS_HIGH_IMPACT_WINDOW_MINUTES", "45"))
    stale_after_minutes = int(os.getenv("NEWS_STALE_AFTER_MINUTES", "720"))
    relevant_currencies = _currencies_for_symbol(symbol)
    provider_enabled = os.getenv("NEWS_PROVIDER_ENABLED", "false").lower() == "true"

    relevant_events = [
        event
        for event in events
        if not relevant_currencies or relevant_currencies.intersection(event.currencies)
    ]
    upcoming_high = [
        event
        for event in relevant_events
        if event.impact in HIGH_IMPACT_LEVELS and now <= event.event_time <= now + timedelta(minutes=high_impact_window)
    ]
    future_high = [event for event in relevant_events if event.impact in HIGH_IMPACT_LEVELS and event.event_time >= now]
    next_high = future_high[0] if future_high else None
    last_event = max(events, key=lambda item: item.event_time, default=None)
    provider_fresh = bool(events) and last_event is not None and last_event.event_time >= now - timedelta(minutes=stale_after_minutes)
    fail_safe = (not provider_enabled) or bool(error) or not provider_fresh
    halt_active = fail_safe or bool(upcoming_high)
    high_impact_next_minutes = None
    if next_high:
        high_impact_next_minutes = max(0, int((next_high.event_time - now).total_seconds() / 60))

    if not provider_enabled:
        note = "News provider is disabled; news-sensitive trading remains halted."
    elif error:
        note = "News provider is configured but not healthy; news-sensitive trading remains halted."
    elif not provider_fresh:
        note = "News provider has no fresh events; news-sensitive trading remains halted."
    elif upcoming_high:
        note = "High-impact event is inside the configured halt window."
    else:
        note = "News provider is healthy and no high-impact halt window is active."

    return {
        "symbol": symbol,
        "provider_enabled": provider_enabled,
        "provider_type": provider_type,
        "provider_fresh": provider_fresh,
        "provider_error": error,
        "relevant_currencies": sorted(relevant_currencies),
        "high_impact_window_minutes": high_impact_window,
        "high_impact_next_minutes": high_impact_next_minutes,
        "news_halt_active": halt_active,
        "risk_status": "news_safe_mode" if halt_active else "news_clear",
        "events_count": len(events),
        "relevant_events_count": len(relevant_events),
        "upcoming_high_impact_events": [event.to_dict() for event in upcoming_high[:10]],
        "next_high_impact_event": next_high.to_dict() if next_high else None,
        "note": note,
    }


def list_news_events(symbol: str | None = None, limit: int = 50) -> dict[str, Any]:
    provider_type, events, error = _load_provider_events()
    relevant_currencies = _currencies_for_symbol(symbol)
    if relevant_currencies:
        events = [event for event in events if relevant_currencies.intersection(event.currencies)]
    return {
        "symbol": symbol,
        "provider_type": provider_type,
        "provider_error": error,
        "events": [event.to_dict() for event in events[: max(1, min(limit, 200))]],
    }
