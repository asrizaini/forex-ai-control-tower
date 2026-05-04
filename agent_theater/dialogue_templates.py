from __future__ import annotations

from typing import Any


def market_dialogue(worker_name: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots = result.get("snapshots", [])
    primary = snapshots[0] if snapshots else {}
    monitored = [str(item.get("symbol")) for item in snapshots if isinstance(item, dict) and item.get("symbol")]
    symbol = primary.get("symbol", "watchlist")
    trend = primary.get("trend", "unknown")
    spread = primary.get("spread")
    freshness = primary.get("freshness_seconds")
    indicators = primary.get("indicators", {}) if isinstance(primary.get("indicators"), dict) else {}
    rsi_14 = indicators.get("rsi_14")
    ema_20 = indicators.get("ema_20")
    ema_50 = indicators.get("ema_50")
    if result.get("bridge_connected") and primary and primary.get("feed_fresh") and primary.get("rates_count", 0) > 0:
        market_summary = (
            f"{len(monitored)} enabled pairs are being processed: {', '.join(monitored)}. Primary view {symbol} is live from MT5 bridge; latest short-term trend reads {trend}; "
            f"spread is {spread if spread is not None else 'unknown'} and tick age is {freshness if freshness is not None else 'unknown'} seconds."
        )
        technical_summary = (
            f"Multi-pair candle snapshots received. Primary {symbol} has {primary.get('rates_count', 0)} M1 candles. "
            f"Technical bias is {trend}; EMA20={ema_20 if ema_20 is not None else 'n/a'}, "
            f"EMA50={ema_50 if ema_50 is not None else 'n/a'}, RSI14={rsi_14 if rsi_14 is not None else 'n/a'}. "
            "No BUY/SELL signal is authorized because strategy governance is still monitor-only."
        )
        market_result = "mt5_market_data_live"
        adapter_status = "connected"
    elif result.get("bridge_connected") and primary:
        market_summary = (
            f"MT5 bridge is reachable for {symbol}, but market data is limited right now across the enabled watchlist. "
            f"Tick age is {freshness if freshness is not None else 'unknown'} seconds and M1 candles received: {primary.get('rates_count', 0)}."
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
    news_status = news_statuses.get(symbol, {}) if isinstance(news_statuses, dict) else {}
    if news_status and news_status.get("provider_enabled") and news_status.get("provider_fresh"):
        if news_status.get("news_halt_active"):
            next_event = news_status.get("next_high_impact_event") or {}
            news_summary = (
                f"News feed is connected for {symbol}, but I am keeping the halt active. "
                f"Next high-impact event: {next_event.get('title', 'scheduled event')} in "
                f"{news_status.get('high_impact_next_minutes', 'unknown')} minutes."
            )
            news_result = "high_impact_halt_active"
            news_confidence = 0.84
        else:
            news_summary = (
                f"News feed is connected for {symbol}. No high-impact event is inside the configured halt window; "
                "news-sensitive strategies may continue to risk review."
            )
            news_result = "news_clear"
            news_confidence = 0.86
        news_sources = [f"news provider: {news_status.get('provider_type', 'configured')}"]
        news_connected = True
        news_next_action = "Keep feeding news status into Execution Guard inputs before any signal is approved."
    else:
        news_summary = (
            f"News feed is not verified for {symbol}. "
            "I am keeping news-sensitive strategies halted until the provider is enabled, fresh, and audited."
        )
        news_result = "pending_or_stale_adapter"
        news_confidence = 0.55
        news_sources = ["news provider status", "safe halt policy"]
        news_connected = False
        news_next_action = "Configure NEWS_PROVIDER_TYPE with a reviewed calendar file or HTTPS provider URL, then verify /api/v1/news/status."
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
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "signal_authorized": True, "symbols_monitored": monitored},
        },
        {
            "agent": "News Agent",
            "stream": "Live Chat View",
            "summary": news_summary,
            "input_sources": news_sources,
            "result": news_result,
            "confidence": news_confidence,
            "risk_status": news_status.get("risk_status", "news_safe_mode") if news_status else "news_safe_mode",
            "next_action": news_next_action,
            "metadata": {
                "worker": worker_name,
                "message_type": "human_dialogue",
                "news_feed_connected": news_connected,
                "provider_type": news_status.get("provider_type") if news_status else None,
            },
        },
    ]


def strategy_risk_dialogue(worker_name: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    account = result.get("account", {})
    if result.get("bridge_connected") and account:
        risk_summary = (
            f"MT5 demo account {account.get('login_masked', '***')} on {account.get('server', 'unknown')} is visible. "
            f"Equity is {account.get('equity', 'unknown')} {account.get('currency', '')}; drawdown is {account.get('drawdown_pct', 'unknown')}%. "
            f"Open positions: {result.get('positions_count', 0)}. Auto execution remains disabled."
        )
        execution_summary = (
            "Execution bridge is reachable, but I am not sending orders. "
            "Order flow still requires strategy approval, risk policy, manual approval, order_check, and Execution Guard token."
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
            "summary": "Notification channels are not connected yet. I will not claim Telegram, WhatsApp, mobile push, or email delivery until credentials and channel tests pass.",
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
