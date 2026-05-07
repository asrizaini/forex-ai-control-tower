from __future__ import annotations

import json
import os
import shutil
import signal
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from agent_theater.loki import push_event


ENDPOINTS = (
    ("Control API", "http://10.10.1.81:8000/health"),
    ("Dashboard", "http://10.10.1.81:5173/healthz"),
    ("Grafana", "http://10.10.1.81:3000/api/health"),
    ("Prometheus", "http://10.10.1.81:9090/-/healthy"),
    ("Qdrant", "http://10.10.1.81:6333/"),
    ("Loki", "http://10.10.1.81:3100/ready"),
    ("Ollama Reason", "http://10.10.1.82:11434/api/tags"),
    ("Ollama Code", "http://10.10.1.83:11434/api/tags"),
    ("MT5 Bridge", "http://10.10.1.86:8501/health"),
)

# Disk-space thresholds (percentage)
DISK_WARNING_PCT = float(os.getenv("DISK_WARNING_PCT", "80"))
DISK_CRITICAL_PCT = float(os.getenv("DISK_CRITICAL_PCT", "90"))
DISK_EMERGENCY_PCT = float(os.getenv("DISK_EMERGENCY_PCT", "95"))

# Service-to-agent mapping for auto-heal dispatch
SERVICE_AGENT_MAP: dict[str, str] = {
    "Control API": "System Improvement Agent",
    "Dashboard": "System Improvement Agent",
    "Grafana": "Watchdog Agent",
    "Prometheus": "Watchdog Agent",
    "Qdrant": "Watchdog Agent",
    "Loki": "Watchdog Agent",
    "Ollama Reason": "System Improvement Agent",
    "Ollama Code": "System Improvement Agent",
    "MT5 Bridge": "Market Data Agent",
}

# Track which services have already had a heal task dispatched (avoid spamming)
_dispatched_heals: dict[str, float] = {}
HEAL_COOLDOWN_SECONDS = int(os.getenv("ORCHESTRATOR_HEAL_COOLDOWN_SECONDS", "300"))

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
    timezone_name = os.getenv("APP_TIMEZONE") or os.getenv("TZ") or "Asia/Kuala_Lumpur"
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        timezone = ZoneInfo("Asia/Kuala_Lumpur")
    return f"{datetime.now(timezone).strftime('%Y-%m-%d %I:%M:%S %p')} GMT+8"


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
    payload = asdict(event)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
    push_event(payload)


def _recent_events(path: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _boardroom_event(path: Path) -> SafeEvent | None:
    recent = _recent_events(path)
    agents = sorted({str(event.get("agent", "Unknown Agent")) for event in recent if event.get("agent")})
    worker_agents = [
        agent
        for agent in agents
        if agent
        in {
            "Market Data Agent",
            "Technical Analysis Agent",
            "News Agent",
            "Strategy Agent",
            "Risk Manager",
            "Risk Manager Agent",
            "Signal Reviewer",
            "Notification Agent",
            "Execution Agent",
        }
    ]
    if not worker_agents:
        return None
    return SafeEvent(
        timestamp=_utc_timestamp(),
        agent="Orchestrator Agent",
        stream="Boardroom Mode",
        summary=f"Team check-in received from {len(worker_agents)} agents: {', '.join(worker_agents)}. Everyone is communicating in safe monitor-only mode.",
        input_sources=worker_agents,
        result="coordination_visible",
        confidence=0.88,
        risk_status="execution_guarded_monitor_only",
        next_action="Continue routing safe summaries into Agent Theater; executable trade flow remains disabled until governance gates pass.",
    )


def _check_disk_space() -> dict[str, Any]:
    """Check disk usage on the PostgreSQL data mount and root filesystem."""
    results: dict[str, Any] = {"pg_disk_pct": None, "root_disk_pct": None, "status": "unknown"}
    try:
        pg_data = os.getenv("PGDATA", "/")
        pg_usage = shutil.disk_usage(pg_data)
        results["pg_disk_pct"] = round(pg_usage.used / pg_usage.total * 100, 1)
    except OSError:
        pass
    try:
        root_usage = shutil.disk_usage("/")
        results["root_disk_pct"] = round(root_usage.used / root_usage.total * 100, 1)
    except OSError:
        pass

    pct = results["pg_disk_pct"] or results["root_disk_pct"]
    if pct is not None:
        if pct >= DISK_EMERGENCY_PCT:
            results["status"] = "emergency"
        elif pct >= DISK_CRITICAL_PCT:
            results["status"] = "critical"
        elif pct >= DISK_WARNING_PCT:
            results["status"] = "warning"
        else:
            results["status"] = "healthy"
    return results


def _disk_event(disk: dict[str, Any]) -> SafeEvent | None:
    """Create an event for disk status if not healthy."""
    status = disk.get("status", "unknown")
    if status == "healthy" or status == "unknown":
        return None

    pct = disk.get("pg_disk_pct") or disk.get("root_disk_pct", "?")
    if status == "emergency":
        summary = f"EMERGENCY: Disk usage at {pct}%. Database writes may fail. Immediate cleanup required."
        result = "disk_emergency"
        risk_status = "execution_halted_disk_full"
        next_action = "Trigger emergency data purge via /api/v1/data-retention/emergency-purge. Add disk capacity if needed."
    elif status == "critical":
        summary = f"CRITICAL: Disk usage at {pct}%. Auto-cleanup should be running. Monitor closely."
        result = "disk_critical"
        risk_status = "execution_guarded_disk_critical"
        next_action = "Verify data-cleanup timer is running. Run /api/v1/data-retention/cleanup manually if needed."
    else:
        summary = f"WARNING: Disk usage at {pct}%. Above warning threshold. Auto-cleanup will engage."
        result = "disk_warning"
        risk_status = "execution_guarded_monitor_only"
        next_action = "Data cleanup worker should handle this automatically. No manual action needed yet."

    return SafeEvent(
        timestamp=_utc_timestamp(),
        agent="Orchestrator Agent",
        stream="Disk Monitor",
        summary=summary,
        input_sources=["disk_monitor"],
        result=result,
        confidence=0.99,
        risk_status=risk_status,
        next_action=next_action,
    )


def _dispatch_heal_task(service_name: str, agent_name: str, error_info: str) -> None:
    """Dispatch an auto-heal task to the database for the workflow engine to pick up.

    Uses cooldown to avoid dispatching duplicate tasks for the same service.
    """
    now = time.time()
    last_dispatch = _dispatched_heals.get(service_name, 0)
    if now - last_dispatch < HEAL_COOLDOWN_SECONDS:
        return  # Still in cooldown

    try:
        from control.api.db import SessionLocal, init_db
        from control.api.models import AgentTask
        from control.api.time_utils import utcnow

        init_db()
        db = SessionLocal()
        try:
            task = AgentTask(
                assigned_agent=agent_name,
                task_type="auto_heal_service_down",
                priority=1,
                request_json={
                    "service_name": service_name,
                    "error_info": error_info,
                    "auto_heal": True,
                    "action": "restart_service",
                    "dispatched_by": "Orchestrator Agent",
                },
            )
            db.add(task)
            db.commit()
            _dispatched_heals[service_name] = now
            print(json.dumps({
                "event": "heal_task_dispatched",
                "service": service_name,
                "agent": agent_name,
            }), flush=True)
        finally:
            db.close()
    except Exception as exc:
        print(json.dumps({
            "event": "heal_dispatch_failed",
            "service": service_name,
            "error": type(exc).__name__,
        }), flush=True)


def _dispatch_disk_heal_task(disk: dict[str, Any]) -> None:
    """Dispatch a disk cleanup task when disk is above warning threshold."""
    now = time.time()
    last_dispatch = _dispatched_heals.get("__disk_cleanup__", 0)
    if now - last_dispatch < HEAL_COOLDOWN_SECONDS:
        return

    status = disk.get("status", "unknown")
    if status in ("warning", "critical", "emergency"):
        try:
            from control.api.db import SessionLocal, init_db
            from control.api.models import AgentTask

            init_db()
            db = SessionLocal()
            try:
                task_type = "disk_emergency_cleanup" if status == "emergency" else "disk_space_cleanup"
                task = AgentTask(
                    assigned_agent="Watchdog Agent",
                    task_type=task_type,
                    priority=0 if status == "emergency" else 1,
                    request_json={
                        "disk_usage_pct": disk.get("pg_disk_pct") or disk.get("root_disk_pct"),
                        "disk_status": status,
                        "action": "emergency_purge" if status == "emergency" else "auto_cleanup",
                        "auto_heal": True,
                        "dispatched_by": "Orchestrator Agent",
                    },
                )
                db.add(task)
                db.commit()
                _dispatched_heals["__disk_cleanup__"] = now
                print(json.dumps({
                    "event": "disk_heal_task_dispatched",
                    "disk_status": status,
                    "agent": "Watchdog Agent",
                }), flush=True)
            finally:
                db.close()
        except Exception as exc:
            print(json.dumps({
                "event": "disk_heal_dispatch_failed",
                "error": type(exc).__name__,
            }), flush=True)


def main() -> int:
    interval_seconds = int(os.getenv("ORCHESTRATOR_INTERVAL_SECONDS", "30"))
    max_events = int(os.getenv("AGENT_THEATER_MAX_EVENTS", "200"))
    event_log = Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    while running:
        # --- 1. HTTP health checks ---
        checks = [_check_http(name, url) for name, url in ENDPOINTS]
        event = _event_from_checks(checks)
        _write_jsonl(event_log, event, max_events)
        print(json.dumps(asdict(event), separators=(",", ":")), flush=True)

        # --- 2. Auto-heal: dispatch tasks for failed services ---
        failed_services = [c for c in checks if not c["ok"]]
        for svc in failed_services:
            agent = SERVICE_AGENT_MAP.get(svc["name"], "Watchdog Agent")
            error_info = f"HTTP {svc.get('status', 0)}" if svc.get("status") else svc.get("error", "unknown")
            _dispatch_heal_task(svc["name"], agent, error_info)

        # --- 3. Disk space check ---
        disk = _check_disk_space()
        disk_event = _disk_event(disk)
        if disk_event:
            _write_jsonl(event_log, disk_event, max_events)
            print(json.dumps(asdict(disk_event), separators=(",", ":")), flush=True)
            # Dispatch disk cleanup task if needed
            _dispatch_disk_heal_task(disk)

        # --- 4. Boardroom coordination ---
        boardroom_event = _boardroom_event(event_log)
        if boardroom_event:
            _write_jsonl(event_log, boardroom_event, max_events)
            print(json.dumps(asdict(boardroom_event), separators=(",", ":")), flush=True)

        time.sleep(interval_seconds)

    return 0


if __name__ == "__main__":
    sys.exit(main())
