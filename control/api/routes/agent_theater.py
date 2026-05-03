from __future__ import annotations

import json
import os
import time
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from agent_theater.loki import push_event
from agent_theater.redaction import redact

router = APIRouter(prefix="/agent-theater", tags=["agent-theater"])

PRIVATE_INGEST_NETWORKS = (
    ip_network("10.10.1.0/24"),
    ip_network("127.0.0.0/8"),
)


class AgentTheaterEventIn(BaseModel):
    agent: str = Field(min_length=1, max_length=80)
    stream: str = Field(default="Live Chat View", max_length=80)
    summary: str = Field(min_length=1, max_length=500)
    input_sources: list[str] = Field(default_factory=list)
    result: str = Field(default="observed", max_length=80)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_status: str = Field(default="execution_guarded_monitor_only", max_length=120)
    next_action: str = Field(default="Continue monitoring.", max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def list_resource() -> dict:
    return {"module": "agent_theater", "description": "Human-readable agent event summaries", "mode": "production-required"}


def _event_log_path() -> Path:
    return Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _ingest_allowed(request: Request, x_agent_event_token: str | None) -> bool:
    expected = os.getenv("AGENT_EVENT_INGEST_TOKEN")
    if expected:
        return bool(x_agent_event_token) and x_agent_event_token == expected
    client_host = request.client.host if request.client else ""
    try:
        client_ip = ip_address(client_host)
    except ValueError:
        return False
    return any(client_ip in network for network in PRIVATE_INGEST_NETWORKS)


def _append_event(event: dict[str, Any]) -> Path:
    event_log = _event_log_path()
    event_log.parent.mkdir(parents=True, exist_ok=True)
    with event_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    push_event(event)
    return event_log


@router.get("/events")
def list_events(limit: int = 50) -> dict:
    event_log = _event_log_path()
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


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
def publish_event(
    event: AgentTheaterEventIn,
    request: Request,
    x_agent_event_token: str | None = Header(default=None),
) -> dict:
    if not _ingest_allowed(request, x_agent_event_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent Theater ingest is restricted")
    payload = redact(event.model_dump())
    payload["timestamp"] = _timestamp()
    payload["contains_hidden_chain_of_thought"] = False
    event_log = _append_event(payload)
    return {"accepted": True, "source": str(event_log)}

