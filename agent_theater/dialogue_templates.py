from __future__ import annotations

import re
from typing import Any


def _canonical_symbol(value: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9]", "", value.strip().upper())
    return cleaned[:6] if len(cleaned) >= 6 else cleaned


def market_dialogue(worker_name: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots = result.get("snapshots", [])
    def _priority(item: dict[str, Any]) -> tuple[int, int, int]:
        tf = str(item.get("timeframe", "M1")).upper()
        tf_rank = {"D1": 7, "H4": 6, "H1": 5, "M30": 4, "M15": 3, "M5": 2, "M1": 1}.get(tf, 0)
        fresh_rank = 1 if item.get("feed_fresh") else 0
        rates_rank = int(item.get("rates_count", 0))
        return (fresh_rank, tf_rank, rates_rank)
    primary = sorted(
        [item for item in snapshots if isinstance(item, dict)],
        key=_priority,
        reverse=True,
    )[0] if snapshots else {}
    monitored: list[str] = []
    timeframe_map: dict[str, set[str]] = {}
    for item in snapshots:
        if not isinstance(item, dict) or not item.get("symbol"):
            continue
        symbol = _canonical_symbol(str(item.get("symbol")))
        if not symbol:
            continue
        if symbol not in monitored:
            monitored.append(symbol)
        tf = str(item.get("timeframe", "M1")).upper()
        timeframe_map.setdefault(symbol, set()).add(tf)
    coverage = ", ".join(
        f"{symbol}({','.join(sorted(timeframe_map.get(symbol, set()))[:4])})"
        for symbol in monitored
    )
    symbol = primary.get("symbol", "watchlist")
    timeframe = str(primary.get("timeframe", "M1"))
    trend = primary.get("trend", "unknown")
    spread = primary.get("spread")
    freshness = primary.get("freshness_seconds")
    indicators = primary.get("indicators", {}) if isinstance(primary.get("indicators"), dict) else {}
    rsi_14 = indicators.get("rsi_14")
    ema_20 = indicators.get("ema_20")
    ema_50 = indicators.get("ema_50")
    if result.get("bridge_connected") and primary and primary.get("feed_fresh") and primary.get("rates_count", 0) > 0:
        market_summary = (
            f"{len(monitored)} enabled pairs are being processed: {', '.join(monitored)}. Timeframe coverage: {coverage}. "
            f"Primary view {symbol} {timeframe} is live from MT5 bridge; latest short-term trend reads {trend}; "
            f"spread is {spread if spread is not None else 'unknown'} and tick age is {freshness if freshness is not None else 'unknown'} seconds."
        )
        technical_summary = (
            f"Multi-pair candle snapshots received. Primary {symbol} {timeframe} has {primary.get('rates_count', 0)} candles. "
            f"Technical bias is {trend}; EMA20={ema_20 if ema_20 is not None else 'n/a'}, "
            f"EMA50={ema_50 if ema_50 is not None else 'n/a'}, RSI14={rsi_14 if rsi_14 is not None else 'n/a'}. "
            "BUY/SELL setup quality is visible, but execution remains governance-gated."
        )
        market_result = "mt5_market_data_live"
        adapter_status = "connected"
    elif result.get("bridge_connected") and primary:
        market_summary = (
            f"MT5 bridge is reachable for {symbol}, but market data is limited right now across the enabled watchlist. "
            f"Tick age is {freshness if freshness is not None else 'unknown'} seconds and {timeframe} candles received: {primary.get('rates_count', 0)}. "
            f"Coverage snapshot: {coverage}."
        )
        technical_summary = (
            f"{symbol} does not have enough fresh candles for trusted technical analysis. "
            "I am blocking signal commentary until the feed becomes fresh and candle history is available."
        )
        market_result = "mt5_market_data_stale_or_limited"
        adapter_status = "limited"
    else:
        market_summary = (
            "Market worker is running, but MT5 bridge market data is not fully available to this worker yet. "
            "I will keep analysis conservative until bridge token, symbols, ticks, and candles all pass."
        )
        technical_summary = "Technical Analysis Agent is standing by for validated candle data before producing any setup commentary."
        market_result = result.get("status", "degraded")
        adapter_status = "degraded"
    news_statuses = result.get("news_statuses", {})
    status_map = news_statuses if isinstance(news_statuses, dict) else {}
    selected = [status_map.get(item["symbol"], {}) for item in snapshots if item.get("symbol")]
    selected = [item for item in selected if isinstance(item, dict) and item]
    provider_connected = [item for item in selected if item.get("provider_enabled") and item.get("provider_fresh")]
    halted = [item for item in selected if item.get("news_halt_active")]
    provider_type = next((item.get("provider_type") for item in provider_connected if item.get("provider_type")), None)
    if provider_connected:
        if halted:
            next_event = halted[0].get("next_high_impact_event") or {}
            next_minutes = halted[0].get("high_impact_next_minutes", "unknown")
            news_summary = (
                f"News feed is live for {len(provider_connected)} pair(s). "
                f"High-impact halt is active on {len(halted)} pair(s). Next event: {next_event.get('title', 'scheduled event')} in {next_minutes} minutes."
            )
            news_result = "high_impact_halt_active"
            news_confidence = 0.84
        else:
            news_summary = (
                f"News feed is live for {len(provider_connected)} pair(s). "
                "No high-impact event is inside the configured halt window; news-sensitive strategies can move to risk review."
            )
            news_result = "news_clear"
            news_confidence = 0.86
        news_sources = [f"news provider: {provider_type or 'configured'}", "multi-pair news status"]
        news_connected = True
        news_next_action = "Continue feeding pair-level news risk into Execution Guard before any signal is approved."
        news_risk_status = "news_safe_mode" if halted else "news_clear"
    else:
        news_summary = (
            "News feed is not verified for the enabled pair set. "
            "I am keeping news-sensitive strategies halted until the provider is enabled, fresh, and audited."
        )
        news_result = "pending_or_stale_adapter"
        news_confidence = 0.55
        news_sources = ["news provider status", "safe halt policy"]
        news_connected = False
        news_next_action = "Configure NEWS_PROVIDER_TYPE and NEWS_PROVIDER_API_KEY, then verify /api/v1/news/status."
        news_risk_status = "news_safe_mode"
    return [
        {
            "agent": "Market Data Agent",
            "stream": "Live Chat View",
            "summary": market_summary,
            "input_sources": ["fx-market-worker", "MT5 Bridge", "market_worker.py"],
            "result": market_result,
            "confidence": 0.9 if adapter_status == "connected" else 0.66 if adapter_status == "limited" else 0.58,
            "risk_status": f"market_data_{result.get('data_quality', 'limited')}_monitor_only",
            "next_action": "Continue feed-quality checks; do not authorize executable signals until strategy and risk gates are wired.",
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "adapter_status": adapter_status, "symbols_monitored": monitored},
        },
        {
            "agent": "Technical Analysis Agent",
            "stream": "Strategy War Room",
            "summary": technical_summary,
            "input_sources": ["Market Data Agent"],
            "result": "analysis_visible_no_signal",
            "confidence": 0.78 if adapter_status == "connected" else 0.62 if adapter_status == "limited" else 0.56,
            "risk_status": "no_execution_requested",
            "next_action": "Build indicator and multi-timeframe confirmation before any demo signal proposal.",
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "signal_authorized": False, "symbols_monitored": monitored},
        },
        {
            "agent": "News Agent",
            "stream": "Live Chat View",
            "summary": news_summary,
            "input_sources": news_sources,
            "result": news_result,
            "confidence": news_confidence,
            "risk_status": news_risk_status,
            "next_action": news_next_action,
            "metadata": {
                "worker": worker_name,
                "message_type": "human_dialogue",
                "news_feed_connected": news_connected,
                "provider_type": provider_type,
                "pairs_with_news_status": len(selected),
                "pairs_halted_by_news": len(halted),
            },
        },
    ]


def strategy_risk_dialogue(worker_name: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    account = result.get("account", {})
    cycle = result.get("demo_execution_cycle", {}) if isinstance(result.get("demo_execution_cycle"), dict) else {}
    sent = int(cycle.get("sent", 0))
    blocked = int(cycle.get("blocked", 0))
    failed = int(cycle.get("failed", 0))
    if result.get("bridge_connected") and account:
        risk_summary = (
            f"MT5 demo account {account.get('login_masked', '***')} on {account.get('server', 'unknown')} is visible. "
            f"Equity is {account.get('equity', 'unknown')} {account.get('currency', '')}; drawdown is {account.get('drawdown_pct', 'unknown')}%. "
            f"Open positions: {result.get('positions_count', 0)}. Demo cycle result: sent {sent}, blocked {blocked}, failed {failed}."
        )
        execution_summary = (
            "Execution bridge is reachable. Demo execution cycle can send orders only when strategy, risk, order_check, and Execution Guard checks all pass."
        )
        risk_confidence = 0.92
    else:
        risk_summary = "Risk worker is running, but MT5 account visibility is degraded. Execution remains blocked until account and position checks are reliable."
        execution_summary = "Execution is blocked because account/bridge validation is not fully healthy."
        risk_confidence = 0.64
    return [
        {
            "agent": "Strategy Agent",
            "stream": "Strategy War Room",
            "summary": "Strategy registry database is online. Operator-approved monitor-only signal generation is active for enabled pairs; executable orders still require strategy governance, risk approval, manual approval, and Execution Guard.",
            "input_sources": ["strategy registry", "fx-strategy-risk-worker"],
            "result": "monitor_signal_generation_ready",
            "confidence": 0.84,
            "risk_status": "strategy_lifecycle_guarded_no_execution",
            "next_action": "Use the Signals and Testing pages to validate monitor-only outputs before demo manual approval workflows.",
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "approved_signal": True},
        },
        {
            "agent": "Risk Manager",
            "stream": "Account Routing Room",
            "summary": risk_summary,
            "input_sources": ["risk policy database", "Execution Guard", "MT5 Bridge"],
            "result": "guarded",
            "confidence": risk_confidence,
            "risk_status": "auto_execution_disabled",
            "next_action": "Create per-account demo risk policy before any manual approval workflow is activated.",
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "live_auto_trading": False},
        },
        {
            "agent": "Signal Reviewer",
            "stream": "Boardroom Mode",
            "summary": "No live setup is under review. When Strategy Agent proposes a demo signal, I will check score, rationale, duplicate risk, and approval requirements.",
            "input_sources": ["Strategy Agent", "Risk Manager"],
            "result": "waiting_for_signal",
            "confidence": 0.78,
            "risk_status": "manual_review_required",
            "next_action": "Wait for a validated demo signal proposal; do not forward anything to execution yet.",
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "signal_review_active": False},
        },
        {
            "agent": "Notification Agent",
            "stream": "Live Chat View",
            "summary": "Notification channels are not connected yet. I will not claim Telegram or mobile push delivery until credentials and channel tests pass.",
            "input_sources": ["notification hub scaffold"],
            "result": "pending_adapter",
            "confidence": 0.6,
            "risk_status": "no_approval_delivery_channel",
            "next_action": "Configure Telegram first, then test dashboard approval requests in demo mode.",
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "telegram_connected": False},
        },
        {
            "agent": "Execution Agent",
            "stream": "Account Routing Room",
            "summary": execution_summary,
            "input_sources": ["Execution Guard", "MT5 Bridge"],
            "result": "blocked_by_design",
            "confidence": 0.96,
            "risk_status": "order_send_blocked_without_guard_token",
            "next_action": "Stay in monitor-only mode until approval workflow and demo risk policy are complete.",
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "order_sent": False},
        },
    ]
