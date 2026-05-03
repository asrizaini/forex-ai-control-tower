from __future__ import annotations

from typing import Any

from .mt5_bridge_client import bridge_account, bridge_health, bridge_positions, mask_login


def _account_body(response: dict[str, Any]) -> dict[str, Any]:
    return response.get("body", {}) if response.get("ok") else {}


def _drawdown_pct(account: dict[str, Any]) -> float | None:
    try:
        balance = float(account["balance"])
        equity = float(account["equity"])
    except (KeyError, TypeError, ValueError):
        return None
    if balance <= 0:
        return None
    return round(max(0.0, (balance - equity) / balance * 100), 2)


def run_strategy_risk_worker_once() -> dict[str, Any]:
    health = bridge_health()
    account_response = bridge_account()
    positions_response = bridge_positions()
    account = _account_body(account_response)
    positions = positions_response.get("body", {}).get("positions", []) if positions_response.get("ok") else []
    drawdown = _drawdown_pct(account)
    bridge_connected = bool(health.get("body", {}).get("mt5_connected")) if health.get("ok") else False
    return {
        "worker": "strategy_risk",
        "status": "ready" if bridge_connected and account_response.get("ok") else "degraded",
        "bridge_connected": bridge_connected,
        "account": {
            "login_masked": mask_login(account.get("login")),
            "server": account.get("server", "unknown"),
            "currency": account.get("currency", "unknown"),
            "balance": account.get("balance"),
            "equity": account.get("equity"),
            "margin_free": account.get("margin_free"),
            "trade_allowed": account.get("trade_allowed"),
            "drawdown_pct": drawdown,
        },
        "positions_count": len(positions),
        "risk_mode": "monitor_only",
        "auto_execution_enabled": False,
        "order_routing": "blocked_until_governance",
    }
