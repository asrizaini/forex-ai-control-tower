from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/agent-theater", tags=["agent-theater"])


@router.get("")
def list_resource() -> dict:
    return {"module": "agent_theater", "description": "Human-readable agent event summaries", "mode": "production-required"}


@router.get("/events")
def list_events(limit: int = 50) -> dict:
    event_log = Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))
    if not event_log.exists():
        return {"events": [], "source": str(event_log)}
    lines = event_log.read_text(encoding="utf-8").splitlines()[-max(1, min(limit, 200)) :]
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"events": events, "source": str(event_log)}

