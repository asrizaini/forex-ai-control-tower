from __future__ import annotations

from datetime import datetime
import os
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _timestamp() -> str:
    timezone_name = os.getenv("APP_TIMEZONE") or os.getenv("TZ") or "Asia/Kuala_Lumpur"
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        timezone = ZoneInfo("Asia/Kuala_Lumpur")
        timezone_name = "Asia/Kuala_Lumpur"
    return f"{datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S')} {timezone_name}"


def room_seed_events(room_name: str, session_id: str = "room-seed") -> list[dict[str, Any]]:
    common = {
        "input_sources": ["Agent Theater room catalog", "Control plane status"],
        "confidence": 0.84,
        "metadata": {"session_id": session_id, "message_type": "room_seed"},
        "timestamp": _timestamp(),
        "contains_hidden_chain_of_thought": False,
    }
    templates: dict[str, list[dict[str, Any]]] = {
        "Workflow Timeline": [
            {
                "agent": "Orchestrator Agent",
                "summary": "Workflow lane opened. I will track each governed step from signal intake through validation, approval, execution guard, MT5 bridge, and journal.",
                "result": "workflow_opened",
                "risk_status": "no_execution_requested",
                "next_action": "Wait for a validated signal or operator task before advancing the workflow.",
            },
            {
                "agent": "Signal Reviewer",
                "summary": "No signal is currently queued for approval. When one arrives, I will show score, rationale, duplicate-risk status, and required approver.",
                "result": "waiting_for_signal",
                "risk_status": "manual_review_required",
                "next_action": "Keep the timeline idle until Strategy Agent creates a demo-safe proposal.",
            },
            {
                "agent": "Journal Agent",
                "summary": "Journal lane is ready. Any approval, rejection, simulation, or MT5 bridge result will be recorded as an auditable event.",
                "result": "journal_ready",
                "risk_status": "append_only_audit",
                "next_action": "Record only safe summaries and references, never secrets or hidden reasoning.",
            },
        ],
        "Boardroom Mode": [
            {
                "agent": "Orchestrator Agent",
                "summary": "Boardroom view is active. Current executive posture is monitor-only: infrastructure is running, MT5 demo is connected, and live trading remains disabled.",
                "result": "executive_status_visible",
                "risk_status": "monitor_only",
                "next_action": "Review readiness by domain: market data, risk, strategy governance, notifications, and broker compatibility.",
            },
            {
                "agent": "Risk Manager",
                "summary": "Risk posture remains conservative. Execution requires account, user, strategy, risk-policy, health, and kill-switch checks before any token can be issued.",
                "result": "risk_posture_visible",
                "risk_status": "execution_guarded",
                "next_action": "Approve only demo workflows after strategy and notification gates are complete.",
            },
            {
                "agent": "Security Review Agent",
                "summary": "Security review is active. Runtime secrets are environment-driven, redaction is enabled, and Agent Theater does not display secret values.",
                "result": "security_posture_visible",
                "risk_status": "secrets_not_displayed",
                "next_action": "Keep production-live blocked until external secret manager and governance approvals are complete.",
            },
        ],
        "Strategy War Room": [
            {
                "agent": "Strategy Agent",
                "summary": "Strategy War Room is active. I can discuss strategy ideas and registry status, but no executable BUY/SELL setup is approved yet.",
                "result": "strategy_room_ready",
                "risk_status": "strategy_lifecycle_guarded",
                "next_action": "Wire plugin loading, test gates, and approval records before demo signal proposals.",
            },
            {
                "agent": "Backtest Agent",
                "summary": "Backtest lane is waiting for historical data and strategy plugins. Until that exists, promotion to demo or live remains blocked.",
                "result": "backtest_pending",
                "risk_status": "validation_required",
                "next_action": "Implement durable historical data storage and repeatable test reports.",
            },
            {
                "agent": "Strategy Promotion Agent",
                "summary": "Promotion gate is closed. A strategy must pass backtest, forward test, paper/demo validation, and admin approval before restricted live use.",
                "result": "promotion_blocked_by_design",
                "risk_status": "governance_required",
                "next_action": "Create the strategy approval workflow and rollback target records.",
            },
        ],
        "Account Routing Room": [
            {
                "agent": "Account Router Agent",
                "summary": "Account Routing Room is active. Signal is global, but every account must pass its own risk, permission, and trading-mode checks.",
                "result": "routing_room_ready",
                "risk_status": "per_account_risk_required",
                "next_action": "Use account profiles and risk policies before routing any demo signal.",
            },
            {
                "agent": "Risk Manager",
                "summary": "Per-account guardrails are active. Kill switches, drawdown limits, open-trade limits, spread/slippage, and market quality can block routing.",
                "result": "account_risk_visible",
                "risk_status": "execution_guarded",
                "next_action": "Bind MT5 account telemetry into the guard check before demo approvals.",
            },
            {
                "agent": "Execution Agent",
                "summary": "Execution lane is waiting. I cannot send directly to MT5; I need a valid Execution Guard token and prior order_check.",
                "result": "execution_waiting",
                "risk_status": "order_send_guarded",
                "next_action": "Remain in monitor-only until governed demo workflow is complete.",
            },
        ],
    }
    base_events = templates.get(
        room_name,
        [
            {
                "agent": "Orchestrator Agent",
                "summary": f"{room_name} is active. I will show safe conclusions, confidence, risk status, and next action only.",
                "result": "room_active",
                "risk_status": "safe_display_only",
                "next_action": "Use this room for visibility and governed coordination; it cannot bypass approvals.",
            }
        ],
    )
    return [{**common, **event, "stream": room_name} for event in base_events]
