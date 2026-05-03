from __future__ import annotations

import json
import os
import signal
import sys
import time
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
        except Exception as exc:  # pragma: no cover - defensive service boundary
            emit({"level": "error", "event": "worker_error", "worker": worker_name, "error": type(exc).__name__})
        elapsed = time.time() - started
        time.sleep(max(1, interval_seconds - int(elapsed)))

    emit({"level": "info", "event": "worker_stopped", "worker": worker_name})
    return 0


if __name__ == "__main__":
    sys.exit(main())
