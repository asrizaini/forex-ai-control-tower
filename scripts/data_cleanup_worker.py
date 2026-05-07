#!/usr/bin/env python3
"""Automatic disk-space cleanup worker.

Runs as a systemd timer (or cron job) to:
1. Check PostgreSQL disk usage
2. If above warning threshold, run data retention cleanup
3. If still critical after cleanup, reduce retention aggressively
4. Log results to the agent theater event log

Designed to be called every 15 minutes via systemd timer.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure the project root is on the Python path
project_root = os.getenv("FOREX_AI_PROJECT_ROOT", "/opt/forex-ai-control-tower")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from control.api.db import SessionLocal, init_db
from control.api.models import AgentTask
from control.api.time_utils import utcnow
from control.api.routes.data_retention import (
    DISK_CRITICAL_PCT,
    DISK_EMERGENCY_PCT,
    DISK_WARNING_PCT,
    auto_cleanup_if_needed,
    _disk_status_label,
    _pg_disk_usage_pct,
)
from agent_theater.loki import push_event


def _write_event_log(event: dict) -> None:
    """Append event to the agent theater event log."""
    event_log = Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))
    event_log.parent.mkdir(parents=True, exist_ok=True)
    with event_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    push_event(event)


def _queue_watchdog_task(disk_pct: float, status: str) -> None:
    """Queue a watchdog agent task when disk is in warning/critical state."""
    init_db()
    db = SessionLocal()
    try:
        task = AgentTask(
            assigned_agent="Watchdog Agent",
            task_type="disk_space_alert",
            priority=1,  # High priority
            request_json={
                "disk_usage_pct": disk_pct,
                "disk_status": status,
                "action_required": "cleanup" if status == "warning" else "emergency_cleanup",
                "auto_cleanup_triggered": True,
            },
        )
        db.add(task)
        db.commit()
    finally:
        db.close()


def main() -> int:
    init_db()

    disk_pct = _pg_disk_usage_pct()
    status = _disk_status_label()

    print(f"[data-cleanup-worker] Disk: {disk_pct}% status={status}", flush=True)

    if disk_pct is not None and disk_pct >= DISK_WARNING_PCT:
        print(f"[data-cleanup-worker] Disk above warning threshold ({DISK_WARNING_PCT}%). Running auto-cleanup...", flush=True)

        # Run automatic cleanup
        result = auto_cleanup_if_needed()

        if result:
            # Log the cleanup event to agent theater
            event = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p GMT+8"),
                "agent": "Data Cleanup Worker",
                "stream": "System Health",
                "summary": f"Auto-cleanup triggered: disk was at {result.get('disk_before_pct')}% ({status}). "
                           f"Cleaned {len(result.get('cleanup_results', []))} tables. "
                           f"Disk now at {result.get('disk_after_pct')}%.",
                "input_sources": ["disk_monitor", "data_retention"],
                "result": "auto_cleanup_completed",
                "confidence": 0.95,
                "risk_status": "execution_guarded_monitor_only",
                "next_action": "Monitor disk usage. If still critical, consider emergency purge.",
                "metadata": result,
                "contains_hidden_chain_of_thought": False,
            }
            _write_event_log(event)

            # Queue a watchdog task so the orchestrator knows about it
            new_pct = result.get("disk_after_pct") or disk_pct
            new_status = _disk_status_label()
            _queue_watchdog_task(new_pct, new_status)

            print(f"[data-cleanup-worker] Cleanup complete. Disk: {new_pct}% status={new_status}", flush=True)

            # If still in emergency after cleanup, log critical alert
            if new_pct is not None and new_pct >= DISK_EMERGENCY_PCT:
                emergency_event = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p GMT+8"),
                    "agent": "Data Cleanup Worker",
                    "stream": "Critical Alert",
                    "summary": f"EMERGENCY: Disk still at {new_pct}% after auto-cleanup. Manual intervention required.",
                    "input_sources": ["disk_monitor"],
                    "result": "emergency_disk_alert",
                    "confidence": 1.0,
                    "risk_status": "execution_halted_disk_full",
                    "next_action": "Run emergency purge via /api/v1/data-retention/emergency-purge or add disk capacity.",
                    "contains_hidden_chain_of_thought": False,
                }
                _write_event_log(emergency_event)
                print(f"[data-cleanup-worker] EMERGENCY: Disk still at {new_pct}%!", flush=True)
                return 2  # Exit code 2 = emergency
        else:
            print("[data-cleanup-worker] Auto-cleanup returned no results (nothing to clean).", flush=True)
    else:
        # Disk is healthy - just log a brief status
        print(f"[data-cleanup-worker] Disk healthy ({disk_pct}%). No cleanup needed.", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())