from __future__ import annotations

from typing import Any


def market_dialogue(worker_name: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots = result.get("snapshots", [])
    primary = snapshots[0] if snapshots else {}
    symbol = primary.get("symbol", "watchlist")
    trend = primary.get("trend", "unknown")
    spread = primary.get("spread")
    freshness = primary.get("freshness_seconds")
    if result.get("bridge_connected") and primary and primary.get("feed_fresh") and primary.get("rates_count", 0) > 0:
        market_summary = (
            f"{symbol} feed is live from MT5 bridge. Latest short-term trend reads {trend}; "
            f"spread is {spread if spread is not None else 'unknown'} and tick age is {freshness if freshness is not None else 'unknown'} seconds."
        )
        technical_summary = (
            f"{symbol} candle snapshot received with {primary.get('rates_count', 0)} M1 candles. "
            f"Technical bias is {trend}, but no BUY/SELL signal is authorized because strategy governance is still monitor-only."
        )
        market_result = "mt5_market_data_live"
        adapter_status = "connected"
    elif result.get("bridge_connected") and primary:
        market_summary = (
            f"MT5 bridge is reachable for {symbol}, but market data is limited right now. "
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
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "adapter_status": adapter_status},
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
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "signal_authorized": False},
        },
        {
            "agent": "News Agent",
            "stream": "Live Chat View",
            "summary": "News adapter is not connected yet. Until ForexFactory/economic-calendar integration is live, high-impact news status stays conservative.",
            "input_sources": ["news adapter placeholder"],
            "result": "pending_adapter",
            "confidence": 0.5,
            "risk_status": "news_safe_mode",
            "next_action": "Wire a news provider and default to blocking news-sensitive strategies when news freshness is unknown.",
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "news_feed_connected": False},
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
            "summary": "Strategy registry database is online. No strategy is approved to generate executable BUY/SELL setups yet; current mode is monitor-only.",
            "input_sources": ["strategy registry", "fx-strategy-risk-worker"],
            "result": result.get("status", "ready"),
            "confidence": 0.84,
            "risk_status": "strategy_lifecycle_guarded",
            "next_action": "Build strategy approval gates, then allow demo-only signal proposals for manual review.",
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "approved_signal": False},
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
