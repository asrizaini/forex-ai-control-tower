from __future__ import annotations

import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from .market_worker import run_market_worker_once
from .strategy_risk_worker import run_strategy_risk_worker_once


WORKERS: dict[str, Callable[[], dict]] = {
    "market": run_market_worker_once,
    "strategy_risk": run_strategy_risk_worker_once,
}

running = True


def _stop(_signum: int, _frame: object) -> None:
    global running
    running = False


def emit(event: dict) -> None:
    print(json.dumps(event, separators=(",", ":")), flush=True)


def theater_events(worker_name: str, result: dict) -> list[dict]:
    if worker_name == "market":
        return [
            {
                "agent": "Market Data Agent",
                "stream": "Live Chat View",
                "summary": "Market worker heartbeat received; candle, tick, spread, and feed-quality loops are alive.",
                "input_sources": ["fx-market-worker", "market_worker.py"],
                "result": result.get("status", "observed"),
                "confidence": 0.86,
                "risk_status": "market_data_monitoring_only",
                "next_action": "Keep collecting market health signals; block execution if feed quality degrades.",
                "metadata": {"worker": worker_name, "safe_mode": True},
            },
            {
                "agent": "Technical Analysis Agent",
                "stream": "Strategy War Room",
                "summary": "Technical analysis loop is standing by for validated candle data; no trade signal is authorized from this heartbeat.",
                "input_sources": ["Market Data Agent"],
                "result": "standby",
                "confidence": 0.72,
                "risk_status": "no_execution_requested",
                "next_action": "Wait for strategy registry and risk gates before producing executable signals.",
                "metadata": {"worker": worker_name, "signal_authorized": False},
            },
        ]
    return [
        {
            "agent": "Strategy Agent",
            "stream": "Boardroom Mode",
            "summary": "Strategy/risk worker heartbeat received; strategy registry, backtest, tuning, and risk loops are alive.",
            "input_sources": ["fx-strategy-risk-worker", "strategy_risk_worker.py"],
            "result": result.get("status", "observed"),
            "confidence": 0.84,
            "risk_status": "execution_guarded_monitor_only",
            "next_action": "Keep strategy lifecycle in monitor mode until governance and validation gates are complete.",
            "metadata": {"worker": worker_name, "safe_mode": True},
        },
        {
            "agent": "Risk Manager Agent",
            "stream": "Account Routing Room",
            "summary": "Risk manager confirms execution remains blocked unless Execution Guard issues a short-lived approval token.",
            "input_sources": ["Strategy Agent", "Execution Guard"],
            "result": "guarded",
            "confidence": 0.9,
            "risk_status": "order_send_blocked_without_guard_token",
            "next_action": "Maintain monitor_only mode while user, account, and strategy permissions are built.",
            "metadata": {"worker": worker_name, "live_auto_trading": False},
        },
    ]


def publish_theater_event(event: dict) -> None:
    url = os.getenv("AGENT_THEATER_INGEST_URL", "http://10.10.1.81:8000/api/v1/agent-theater/events")
    token = os.getenv("AGENT_EVENT_INGEST_TOKEN")
    data = json.dumps(event, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    if token:
        request.add_header("X-Agent-Event-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            emit({"level": "info", "event": "agent_theater_publish", "status": response.status, "agent": event["agent"]})
    except (urllib.error.URLError, TimeoutError) as exc:
        emit({"level": "warning", "event": "agent_theater_publish_failed", "agent": event["agent"], "error": type(exc).__name__})


def main() -> int:
    worker_name = os.getenv("FOREX_WORKER_NAME", "market")
    interval_seconds = int(os.getenv("FOREX_WORKER_INTERVAL_SECONDS", "30"))
    worker = WORKERS.get(worker_name)
    if worker is None:
        emit({"level": "error", "event": "unknown_worker", "worker": worker_name})
        return 2

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    emit({"level": "info", "event": "worker_started", "worker": worker_name})

    while running:
        started = time.time()
        try:
            result = worker()
            emit({"level": "info", "event": "worker_heartbeat", "result": result})
            for theater_event in theater_events(worker_name, result):
                publish_theater_event(theater_event)
        except Exception as exc:  # pragma: no cover - defensive service boundary
            emit({"level": "error", "event": "worker_error", "worker": worker_name, "error": type(exc).__name__})
        elapsed = time.time() - started
        time.sleep(max(1, interval_seconds - int(elapsed)))

    emit({"level": "info", "event": "worker_stopped", "worker": worker_name})
    return 0


if __name__ == "__main__":
    sys.exit(main())
