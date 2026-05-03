from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter

from ..secret_manager import secret_manager_status

router = APIRouter(prefix="/system", tags=["system"])


@router.get("")
def list_resource() -> dict:
    return {"module": "system", "description": "System health, environment, audit, deployment status", "mode": "production-required"}


@router.get("/runtime")
def runtime_status() -> dict:
    event_log = Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))
    return {
        "environment": "demo",
        "trading_mode": "monitor_only",
        "live_auto_trading": False,
        "orchestrator_event_log_exists": event_log.exists(),
        "agent_theater_event_log": str(event_log),
    }


@router.get("/secret-manager/status")
def get_secret_manager_status() -> dict:
    return secret_manager_status()
