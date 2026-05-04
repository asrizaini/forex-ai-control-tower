from __future__ import annotations

import time
import urllib.parse
from typing import Any

from market_data_quality.indicators import indicator_summary

from .mt5_bridge_client import bridge_health, bridge_rates, bridge_symbols, bridge_ticks, configured_watchlist, request_json


def _close_values(rates: list[dict[str, Any]]) -> list[float]:
    values: list[float] = []
    for rate in rates:
        try:
            values.append(float(rate["close"]))
        except (KeyError, TypeError, ValueError):
            continue
    return values


def _trend_from_rates(rates: list[dict[str, Any]]) -> str:
    closes = _close_values(rates)
    if len(closes) < 20:
        return "insufficient_candles"
    fast = sum(closes[-5:]) / 5
    slow = sum(closes[-20:]) / 20
    if fast > slow:
        return "bullish"
    if fast < slow:
        return "bearish"
    return "flat"


def _spread_from_tick(tick: dict[str, Any]) -> float | None:
    try:
        bid = float(tick["bid"])
        ask = float(tick["ask"])
    except (KeyError, TypeError, ValueError):
        return None
    return round(max(0.0, ask - bid), 6)


def _freshness_seconds(tick: dict[str, Any]) -> int | None:
    timestamp = tick.get("time") or tick.get("time_msc")
    try:
        tick_time = int(timestamp)
    except (TypeError, ValueError):
        return None
    if tick_time > 10_000_000_000:
        tick_time = int(tick_time / 1000)
    return max(0, int(time.time()) - tick_time)


def _symbol_snapshot(symbol: str) -> dict[str, Any]:
    rates_response = bridge_rates(symbol)
    tick_response = bridge_ticks(symbol)
    rates = rates_response.get("body", {}).get("rates", []) if rates_response.get("ok") else []
    tick = tick_response.get("body", {}).get("tick", {}) if tick_response.get("ok") else {}
    freshness = _freshness_seconds(tick)
    return {
        "symbol": symbol,
        "timeframe": "M1",
        "rates_ok": bool(rates_response.get("ok")),
        "tick_ok": bool(tick_response.get("ok")),
        "rates_count": len(rates),
        "rates": rates[-100:],
        "trend": _trend_from_rates(rates),
        "indicators": indicator_summary(rates),
        "spread": _spread_from_tick(tick),
        "freshness_seconds": freshness,
        "feed_fresh": freshness is not None and freshness <= 120,
        "last_price": tick.get("last") or tick.get("bid"),
    }


def _news_status(symbol: str) -> dict[str, Any]:
    safe_symbol = urllib.parse.quote(symbol, safe="")
    response = request_json(f"http://10.10.1.81:8000/api/v1/news/status?symbol={safe_symbol}")
    if response.get("ok"):
        return response.get("body", {})
    return {
        "symbol": symbol,
        "provider_enabled": False,
        "provider_fresh": False,
        "news_halt_active": True,
        "risk_status": "news_safe_mode",
        "note": "News status endpoint is unavailable; news-sensitive strategies remain halted.",
    }


def run_market_worker_once() -> dict[str, Any]:
    health = bridge_health()
    symbols_response = bridge_symbols()
    available_symbols = symbols_response.get("body", {}).get("symbols", []) if symbols_response.get("ok") else []
    watchlist = configured_watchlist()
    selected_symbols = [symbol for symbol in watchlist if symbol in available_symbols]
    if not selected_symbols and available_symbols:
        selected_symbols = [str(available_symbols[0])]
    snapshots = [_symbol_snapshot(symbol) for symbol in selected_symbols[:4]]
    news_statuses = {symbol: _news_status(symbol) for symbol in [item["symbol"] for item in snapshots]}
    data_quality = "fresh" if snapshots and all(item["feed_fresh"] for item in snapshots if item["tick_ok"]) else "limited"
    bridge_connected = bool(health.get("body", {}).get("mt5_connected")) if health.get("ok") else False
    return {
        "worker": "market",
        "status": "ready" if bridge_connected else "degraded",
        "bridge_connected": bridge_connected,
        "bridge_status": health.get("body", {}).get("status", "unknown") if health.get("ok") else health.get("error", "unknown"),
        "symbols_available_count": len(available_symbols),
        "watchlist": watchlist,
        "symbols_monitored": [item["symbol"] for item in snapshots],
        "snapshots": snapshots,
        "news_statuses": news_statuses,
        "data_quality": data_quality,
        "order_routing": "disabled_monitor_only",
    }
