from __future__ import annotations

import json
import os
import re
import time
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import decode_token
from ..crud import audit
from ..db import SessionLocal
from agent_theater.loki import push_event
from agent_theater.redaction import redact

router = APIRouter(prefix="/agent-theater", tags=["agent-theater"])

PRIVATE_INGEST_NETWORKS = (
    ip_network("10.10.1.0/24"),
    ip_network("127.0.0.0/8"),
)
PRIVATE_CHAT_NETWORKS = (
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("127.0.0.0/8"),
)
SECRET_TEXT_PATTERN = re.compile(
    r"(password|token|secret|api[_-]?key|broker|credential|bearer\s+[a-z0-9._~+/=-]+)",
    re.IGNORECASE,
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


class OrchestratorChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=800)
    language: str = Field(default="en", pattern="^(en|ms-MY|auto)$")
    session_id: str = Field(default="operator-console", max_length=80)


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


def _chat_allowed(request: Request, authorization: str | None) -> bool:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if decode_token(token):
        return True
    if os.getenv("ORCHESTRATOR_CHAT_INTERNAL_MODE", "true").lower() != "true":
        return False
    client_host = request.client.host if request.client else ""
    try:
        client_ip = ip_address(client_host)
    except ValueError:
        return False
    return any(client_ip in network for network in PRIVATE_CHAT_NETWORKS)


def _safe_chat_text(message: str) -> str:
    normalized = " ".join(message.strip().split())
    if SECRET_TEXT_PATTERN.search(normalized):
        return "[REDACTED: operator message may contain sensitive text]"
    return normalized[:500]


def _append_event(event: dict[str, Any]) -> Path:
    event_log = _event_log_path()
    event_log.parent.mkdir(parents=True, exist_ok=True)
    with event_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    push_event(event)
    return event_log


def _orchestrator_reply(message: str, language: str) -> tuple[str, str]:
    lowered = message.lower()
    if any(word in lowered for word in ("buy", "sell", "order", "trade", "execute", "live", "lot")):
        summary = (
            "I can discuss the trading workflow, but I will not execute or prepare orders from chat. "
            "Execution still requires strategy validation, Risk Manager approval, Account Router checks, "
            "a short-lived Execution Guard token, and manual approval where required."
        )
        next_action = "Use the approvals workflow after demo strategy validation is complete."
    elif any(word in lowered for word in ("status", "health", "ready", "operate", "running")):
        summary = (
            "System status: control API, dashboard, monitoring, worker heartbeats, and Agent Theater are online. "
            "The tower remains in monitor-only safety mode while real market/news/strategy adapters are being wired."
        )
        next_action = "Continue wiring MT5 market data, strategy scoring, approvals, and notification channels."
    elif any(word in lowered for word in ("agent", "theater", "chat", "orchestrator")):
        summary = (
            "This is the operator chat lane. I will answer in human-readable summaries and publish safe replies into "
            "Agent Theater so the team conversation stays visible without exposing hidden reasoning or secrets."
        )
        next_action = "Ask for system status, risk posture, adapter readiness, or the next deployment step."
    elif any(word in lowered for word in ("news", "calendar", "fundamental")):
        summary = (
            "News analysis is still conservative because the live economic-calendar adapter is not connected yet. "
            "Until that integration passes tests, news trading stays blocked by design."
        )
        next_action = "Connect and verify the approved news provider before enabling news-aware signals."
    else:
        summary = (
            "I received your message. I can explain tower status, risk posture, agent activity, deployment progress, "
            "and safe next steps. I cannot bypass governance, risk controls, or MT5 execution rules."
        )
        next_action = "Tell me which part you want to inspect: health, MT5 bridge, strategies, risk, notifications, or agents."
    if language == "ms-MY":
        summary = (
            "Saya terima mesej anda. Saya boleh bantu semak status sistem, risiko, agen, dan langkah seterusnya "
            "dalam bentuk ringkasan selamat. Saya tidak akan melangkaui kelulusan admin, Risk Manager, atau Execution Guard."
        )
        next_action = "Nyatakan bahagian yang anda mahu semak: kesihatan sistem, MT5 bridge, strategi, risiko, notifikasi, atau agen."
    return summary, next_action


def _audit_chat(action: str, session_id: str, details: dict[str, Any]) -> None:
    db: Session = SessionLocal()
    try:
        audit(db, None, action, "orchestrator_chat", session_id, details)
        db.commit()
    finally:
        db.close()


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


@router.post("/chat", status_code=status.HTTP_202_ACCEPTED)
def chat_with_orchestrator(
    payload: OrchestratorChatIn,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    if not _chat_allowed(request, authorization):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    safe_message = _safe_chat_text(payload.message)
    operator_event = {
        "agent": "Operator",
        "stream": "Orchestrator Chat",
        "summary": safe_message,
        "input_sources": ["Dashboard chat"],
        "result": "operator_message_received",
        "confidence": 1.0,
        "risk_status": "read_only_chat_no_execution",
        "next_action": "Orchestrator will answer with a safe status summary.",
        "metadata": {"session_id": payload.session_id, "language": payload.language, "message_type": "operator_chat"},
        "timestamp": _timestamp(),
        "contains_hidden_chain_of_thought": False,
    }
    _append_event(redact(operator_event))

    reply, next_action = _orchestrator_reply(payload.message, payload.language)
    orchestrator_event = {
        "agent": "Orchestrator Agent",
        "stream": "Orchestrator Chat",
        "summary": reply,
        "input_sources": ["Control plane status", "Execution Guard policy", "Agent Theater"],
        "result": "safe_reply",
        "confidence": 0.86,
        "risk_status": "read_only_no_trade_execution",
        "next_action": next_action,
        "metadata": {"session_id": payload.session_id, "language": payload.language, "message_type": "orchestrator_reply"},
        "timestamp": _timestamp(),
        "contains_hidden_chain_of_thought": False,
    }
    _append_event(redact(orchestrator_event))
    _audit_chat(
        "orchestrator_chat",
        payload.session_id,
        {"language": payload.language, "message_redacted": safe_message != " ".join(payload.message.strip().split())},
    )
    return {"accepted": True, "reply": reply, "next_action": next_action}


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

