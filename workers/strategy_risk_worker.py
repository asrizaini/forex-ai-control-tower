from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
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


def _post_demo_execution_cycle() -> dict[str, Any]:
    url = os.getenv("CONTROL_API_URL", "http://10.10.1.81:8000").rstrip("/") + "/api/v1/trades/demo-auto/execute"
    token = os.getenv("DEMO_EXECUTION_RUNNER_TOKEN") or os.getenv("TELEMETRY_INGEST_TOKEN")
    request = urllib.request.Request(url, data=b"{}", method="POST", headers={"Content-Type": "application/json"})
    if token:
        request.add_header("X-Runner-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = json.loads(response.read().decode("utf-8")) if response.length != 0 else {}
            return {"ok": 200 <= response.status < 300, "status": response.status, "body": body}
    except urllib.error.HTTPError as exc:
        payload = {}
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"detail": "http_error"}
        return {"ok": False, "status": exc.code, "body": payload}
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": 0, "body": {"detail": type(exc).__name__}}


def run_strategy_risk_worker_once() -> dict[str, Any]:
    health = bridge_health()
    account_response = bridge_account()
    positions_response = bridge_positions()
    demo_execution_result = _post_demo_execution_cycle()
    account = _account_body(account_response)
    positions = positions_response.get("body", {}).get("positions", []) if positions_response.get("ok") else []
    drawdown = _drawdown_pct(account)
    bridge_connected = bool(health.get("body", {}).get("mt5_connected")) if health.get("ok") else False
    cycle = demo_execution_result.get("body", {}) if isinstance(demo_execution_result.get("body"), dict) else {}
    demo_execution_enabled = bool(cycle.get("trading_mode") == "demo_auto")
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
        "auto_execution_enabled": demo_execution_enabled,
        "order_routing": "demo_execution_cycle_active" if demo_execution_result.get("ok") else "blocked_until_governance",
        "demo_execution_cycle": {
            "ok": bool(demo_execution_result.get("ok")),
            "status": demo_execution_result.get("status"),
            "sent": cycle.get("sent", 0),
            "blocked": cycle.get("blocked", 0),
            "failed": cycle.get("failed", 0),
            "skipped": cycle.get("skipped", 0),
            "candidate_signals": cycle.get("candidate_signals", 0),
            "error": (cycle.get("detail") if not demo_execution_result.get("ok") else None),
        },
    }
