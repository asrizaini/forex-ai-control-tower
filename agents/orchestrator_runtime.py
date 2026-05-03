from __future__ import annotations

import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ENDPOINTS = (
    ("Control API", "http://10.10.1.81:8000/health"),
    ("Dashboard", "http://10.10.1.81:5173/"),
    ("Grafana", "http://10.10.1.81:3000/api/health"),
    ("Prometheus", "http://10.10.1.81:9090/-/healthy"),
    ("Qdrant", "http://10.10.1.81:6333/"),
    ("Loki", "http://10.10.1.81:3100/ready"),
    ("Ollama Reason", "http://10.10.1.82:11434/api/tags"),
    ("Ollama Code", "http://10.10.1.83:11434/api/tags"),
    ("MT5 Bridge", "http://10.10.1.86:8501/health"),
)

running = True


@dataclass(frozen=True)
class SafeEvent:
    timestamp: str
    agent: str
    stream: str
    summary: str
    input_sources: list[str]
    result: str
    confidence: float
    risk_status: str
    next_action: str
    contains_hidden_chain_of_thought: bool = False


def _stop(_signum: int, _frame: object) -> None:
    global running
    running = False


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _check_http(name: str, url: str, timeout_seconds: int = 5) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            body = response.read(256).decode("utf-8", errors="replace")
            return {"name": name, "url": url, "ok": 200 <= response.status < 400, "status": response.status, "body": body}
    except urllib.error.HTTPError as exc:
        return {"name": name, "url": url, "ok": False, "status": exc.code, "body": ""}
    except Exception as exc:
        return {"name": name, "url": url, "ok": False, "status": 0, "error": type(exc).__name__}


def _event_from_checks(checks: list[dict[str, Any]]) -> SafeEvent:
    failed = [item for item in checks if not item["ok"]]
    total = len(checks)
    ok_count = total - len(failed)
    confidence = round(ok_count / total, 2) if total else 0.0
    if failed:
        names = ", ".join(item["name"] for item in failed[:5])
        summary = f"{ok_count}/{total} control tower endpoints healthy. Attention needed: {names}."
        result = "degraded"
        risk_status = "execution_guarded_monitor_only"
        next_action = "Keep trading automation disabled; inspect failed endpoint health and service logs."
    else:
        summary = f"All {total} monitored control tower endpoints are healthy."
        result = "healthy"
        risk_status = "execution_guarded_monitor_only"
        next_action = "Continue monitoring; do not enable live automation until governance gates are complete."

    return SafeEvent(
        timestamp=_utc_timestamp(),
        agent="Orchestrator Agent",
        stream="Live Chat View",
        summary=summary,
        input_sources=[item["name"] for item in checks],
        result=result,
        confidence=confidence,
        risk_status=risk_status,
        next_action=next_action,
    )


def _write_jsonl(path: Path, event: SafeEvent, max_events: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[str] = []
    if path.exists():
        existing = path.read_text(encoding="utf-8").splitlines()[-max_events + 1 :]
    existing.append(json.dumps(asdict(event), separators=(",", ":")))
    path.write_text("\n".join(existing) + "\n", encoding="utf-8")


def main() -> int:
    interval_seconds = int(os.getenv("ORCHESTRATOR_INTERVAL_SECONDS", "30"))
    max_events = int(os.getenv("AGENT_THEATER_MAX_EVENTS", "200"))
    event_log = Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    while running:
        checks = [_check_http(name, url) for name, url in ENDPOINTS]
        event = _event_from_checks(checks)
        _write_jsonl(event_log, event, max_events)
        print(json.dumps(asdict(event), separators=(",", ":")), flush=True)
        time.sleep(interval_seconds)

    return 0


if __name__ == "__main__":
    sys.exit(main())
