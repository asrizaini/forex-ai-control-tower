from __future__ import annotations

from collections import Counter
from typing import Any


def multi_timeframe_summary(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    if not snapshots:
        return {"status": "blocked", "reason": "missing_candles", "trend": "unknown", "fresh": False}
    trends = Counter(str(item.get("trend", "unknown")) for item in snapshots)
    fresh_count = sum(1 for item in snapshots if item.get("feed_fresh"))
    dominant_trend, trend_count = trends.most_common(1)[0]
    return {
        "status": "ok" if fresh_count and dominant_trend != "unknown" else "blocked",
        "trend": dominant_trend,
        "agreement_ratio": round(trend_count / len(snapshots), 2),
        "fresh": fresh_count > 0,
        "snapshots_used": len(snapshots),
    }


def price_action_summary(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not snapshot:
        return {"status": "blocked", "pattern": "unknown", "reason": "missing_snapshot"}
    rates_count = int(snapshot.get("rates_count") or 0)
    trend = str(snapshot.get("trend", "unknown"))
    if rates_count < 20:
        return {"status": "blocked", "pattern": "insufficient_candles", "reason": "need_at_least_20_candles"}
    pattern = "trend_continuation" if trend in {"bullish", "bearish"} else "range_or_unclear"
    return {"status": "ok", "pattern": pattern, "trend": trend, "rates_count": rates_count}


def spread_slippage_summary(snapshot: dict[str, Any] | None, max_spread: float = 25.0, max_slippage: float = 3.0) -> dict[str, Any]:
    if not snapshot:
        return {"status": "blocked", "reason": "missing_snapshot", "spread_ok": False, "slippage_ok": False}
    spread = snapshot.get("spread")
    slippage = snapshot.get("slippage_points")
    spread_ok = spread is not None and float(spread) <= max_spread
    slippage_ok = slippage is None or float(slippage) <= max_slippage
    return {
        "status": "ok" if spread_ok and slippage_ok else "blocked",
        "spread": spread,
        "max_spread": max_spread,
        "spread_ok": spread_ok,
        "slippage_points": slippage,
        "max_slippage": max_slippage,
        "slippage_ok": slippage_ok,
    }
