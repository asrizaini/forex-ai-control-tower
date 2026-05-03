from __future__ import annotations

import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from agent_theater.dialogue_templates import market_dialogue, strategy_risk_dialogue

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
        return market_dialogue(worker_name, result)
    return strategy_risk_dialogue(worker_name, result)


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


def publish_telemetry(worker_name: str, result: dict) -> None:
    url = os.getenv("TELEMETRY_INGEST_URL", "http://10.10.1.81:8000/api/v1/telemetry/worker-snapshot")
    token = os.getenv("TELEMETRY_INGEST_TOKEN")
    data = json.dumps({"worker": worker_name, "result": result}, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    if token:
        request.add_header("X-Telemetry-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            emit({"level": "info", "event": "telemetry_publish", "status": response.status, "worker": worker_name})
    except (urllib.error.URLError, TimeoutError) as exc:
        emit({"level": "warning", "event": "telemetry_publish_failed", "worker": worker_name, "error": type(exc).__name__})


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
            publish_telemetry(worker_name, result)
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
