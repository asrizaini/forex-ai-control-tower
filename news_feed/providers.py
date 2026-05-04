from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Protocol

from news_feed.adapter import _load_provider_events


@dataclass(frozen=True)
class NormalizedCalendarEvent:
    source_id: str
    source: str
    event_time_utc: datetime
    currency: str
    impact: str
    event_name: str
    actual: str = ""
    forecast: str = ""
    previous: str = ""
    revised: str = ""
    detail_url: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def event_uid(self) -> str:
        raw = f"{self.source_id}|{self.currency}|{self.event_name.lower()}|{self.event_time_utc.isoformat()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


@dataclass
class ProviderResult:
    source_id: str
    provider: str
    ok: bool
    events: list[NormalizedCalendarEvent] = field(default_factory=list)
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class CalendarProvider(Protocol):
    source_id: str
    provider: str

    def fetch(self, date_from: date, date_to: date, config: dict[str, Any]) -> ProviderResult:
        ...


def parse_event_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).replace(tzinfo=None)


def normalize_impact(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"red", "high", "critical", "3"}:
        return "high"
    if normalized in {"orange", "medium", "moderate", "2"}:
        return "medium"
    if normalized in {"yellow", "gray", "grey", "low", "minor", "1"}:
        return "low"
    return "unknown"


class ForexFactoryProvider:
    source_id = "forex_factory_calendar"
    provider = "forex_factory"

    def fetch(self, date_from: date, date_to: date, config: dict[str, Any]) -> ProviderResult:
        return ProviderResult(
            source_id=self.source_id,
            provider=self.provider,
            ok=False,
            error="Direct Forex Factory scraping is registered but disabled until operator enables a compliant scraper runtime.",
            metadata={
                "supports_currency_filter": True,
                "supports_impact_filter": True,
                "storage_pattern": "last_run_monthly_history",
                "alert_matching": ["currency", "impact", "keyword", "exact_event_name", "weekday"],
            },
        )


class MarketCalendarToolProvider:
    source_id = "market_calendar_tool"
    provider = "market_calendar_tool"

    def fetch(self, date_from: date, date_to: date, config: dict[str, Any]) -> ProviderResult:
        try:
            import market_calendar_tool  # type: ignore  # noqa: F401
        except Exception:
            return ProviderResult(
                source_id=self.source_id,
                provider=self.provider,
                ok=False,
                error="market-calendar-tool package is not installed in this runtime.",
                metadata={
                    "supported_sites": ["ForexFactory", "MetalsMine", "EnergyExch", "CryptoCraft"],
                    "supports_extended_data": True,
                    "supports_concurrency": True,
                    "recommended_storage": ["csv", "parquet", "metadata"],
                },
            )
        return ProviderResult(
            source_id=self.source_id,
            provider=self.provider,
            ok=False,
            error="market-calendar-tool is available, but live invocation is not wired yet in this safety release.",
        )


class ForexFactoryScrapperApiProvider:
    source_id = "forex_factory_scrapper_api"
    provider = "forex_factory_scrapper_api"

    def fetch(self, date_from: date, date_to: date, config: dict[str, Any]) -> ProviderResult:
        base_url = str(config.get("base_url", "")).strip()
        if not base_url:
            return ProviderResult(
                source_id=self.source_id,
                provider=self.provider,
                ok=False,
                error="ForexFactoryScrapper API base_url is not configured.",
                metadata={"endpoint_shape": "/api/{site}/daily?day=&month=&year=&limit=&offset="},
            )
        return ProviderResult(
            source_id=self.source_id,
            provider=self.provider,
            ok=False,
            error="ForexFactoryScrapper API connector is configured but not executed by this dashboard request.",
            metadata={"base_url_configured": True},
        )


class FmpEconomicCalendarProvider:
    source_id = "fmp_economic_calendar"
    provider = "fmp"

    def fetch(self, date_from: date, date_to: date, config: dict[str, Any]) -> ProviderResult:
        provider_type, events, error = _load_provider_events()
        normalized = [
            NormalizedCalendarEvent(
                source_id=self.source_id,
                source=event.source,
                event_time_utc=event.event_time,
                currency=event.currencies[0] if event.currencies else "",
                impact=event.impact,
                event_name=event.title,
                raw=event.to_dict(),
            )
            for event in events
            if date_from <= event.event_time.date() <= date_to and event.currencies
        ]
        return ProviderResult(
            source_id=self.source_id,
            provider=self.provider,
            ok=not error and bool(normalized),
            events=normalized,
            error=error or ("" if normalized else "No FMP or fallback calendar events returned."),
            metadata={"provider_type": provider_type, "events_count": len(normalized)},
        )


PROVIDERS: dict[str, CalendarProvider] = {
    "forex_factory": ForexFactoryProvider(),
    "market_calendar_tool": MarketCalendarToolProvider(),
    "forex_factory_scrapper_api": ForexFactoryScrapperApiProvider(),
    "fmp": FmpEconomicCalendarProvider(),
    "fmp_economic_calendar": FmpEconomicCalendarProvider(),
}
