from __future__ import annotations

from typing import Any


def market_dialogue(worker_name: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "agent": "Market Data Agent",
            "stream": "Live Chat View",
            "summary": "Hey, market-data worker is alive. Candle and tick collectors are ready, but real symbol analysis is still waiting for the MT5 market-data adapter to be wired.",
            "input_sources": ["fx-market-worker", "market_worker.py"],
            "result": result.get("status", "ready"),
            "confidence": 0.86,
            "risk_status": "market_data_monitoring_only",
            "next_action": "Connect the candle/tick collector to MT5 bridge before publishing real EURUSD or XAUUSD market commentary.",
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "adapter_status": "pending_adapter"},
        },
        {
            "agent": "Technical Analysis Agent",
            "stream": "Strategy War Room",
            "summary": "I am standing by for validated H1/M15 candle data. EMA, RSI, support/resistance, and pullback detection are not producing live trade setups yet.",
            "input_sources": ["Market Data Agent"],
            "result": "standby",
            "confidence": 0.72,
            "risk_status": "no_execution_requested",
            "next_action": "Enable indicator engine only after market data quality checks are active.",
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
            "summary": "Risk is locked down. Global policy allows monitoring only; auto execution is disabled and max trade limits remain zero until admin approval.",
            "input_sources": ["risk policy database", "Execution Guard"],
            "result": "guarded",
            "confidence": 0.9,
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
            "summary": "Execution is waiting. No order will be sent to MT5 unless manual approval and Execution Guard token are both present.",
            "input_sources": ["Execution Guard", "MT5 Bridge"],
            "result": "blocked_by_design",
            "confidence": 0.96,
            "risk_status": "order_send_blocked_without_guard_token",
            "next_action": "Stay in monitor-only mode until approval workflow and demo risk policy are complete.",
            "metadata": {"worker": worker_name, "message_type": "human_dialogue", "order_sent": False},
        },
    ]
