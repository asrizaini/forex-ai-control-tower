from __future__ import annotations

import json
import os
import re
import secrets
import urllib.error
import urllib.request
from ipaddress import ip_address, ip_network
from pathlib import Path
from time import perf_counter, time
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import decode_token
from ..credential_store import runtime_value
from ..crud import audit
from ..db import SessionLocal
from ..models import AgentTask
from ..time_utils import format_local
from agent_theater.loki import push_event
from agent_theater.modes import mode_names, modes_as_dicts
from agent_theater.redaction import redact
from agent_theater.renderer import render_event, render_events
from agent_theater.room_templates import room_seed_events

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

_ORCHESTRATOR_RUNTIME: dict[str, Any] = {
    "last_success_at": None,
    "last_failed_at": None,
    "last_failed_reason": "",
    "last_provider": "static",
    "last_latency_ms": None,
}

PROVIDER_FAILURE_MESSAGE = "Orchestrator AI provider unavailable. Local LLM (Ollama) is unreachable or failed."


def _normalized_provider_mode(raw: str) -> str:
    value = (raw or "").strip().lower()
    aliases = {"ollama": "local", "static": "disabled", "openai": "local"}
    return aliases.get(value, value if value in {"local", "disabled"} else "local")


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
    orchestrator_only: bool = False


@router.get("")
def list_resource() -> dict:
    return {"module": "agent_theater", "description": "Human-readable agent event summaries", "mode": "production-required"}


@router.get("/modes")
def list_modes() -> dict:
    return {"modes": modes_as_dicts()}


def _event_log_path() -> Path:
    return Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))


def _timestamp() -> str:
    return format_local()


def _ingest_allowed(request: Request, x_agent_event_token: str | None) -> bool:
    expected = runtime_value("AGENT_EVENT_INGEST_TOKEN")
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
    if runtime_value("ORCHESTRATOR_CHAT_INTERNAL_MODE", "true").lower() != "true":
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


def _strip_hidden_reasoning(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL).strip()


def _sentence_safe_trim(text: str, limit: int = 650) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    clipped = cleaned[:limit].rsplit(" ", 1)[0]
    sentence_end = max(clipped.rfind("."), clipped.rfind("!"), clipped.rfind("?"))
    if sentence_end > 240:
        return clipped[: sentence_end + 1]
    return clipped.rstrip(" ,;:") + "..."


def _ask_local_llm(message: str, language: str) -> str | None:
    base_url = runtime_value("OLLAMA_REASON_URL", "http://10.10.1.82:11434").rstrip("/")
    model = runtime_value("ORCHESTRATOR_GENERAL_CHAT_MODEL", "llama3.1:8b")
    api_style = runtime_value("LOCAL_LLM_API_STYLE", "ollama").lower()
    api_key = runtime_value("LOCAL_LLM_API_KEY")
    prompt = (
        "You are the Forex AI Control Tower Orchestrator, a safe human-facing assistant. "
        "Answer general questions naturally and helpfully. For trading, deployment, credentials, or system actions, "
        "explain the governed workflow and never claim an unsafe action was executed. Do not reveal hidden reasoning. "
        "Do not ask for or repeat secrets. The Control Tower principle is: AI analyzes, Risk engine controls, "
        "Admin approves, MT5 executes. You do not execute trades yourself. Answer in 3 to 5 short sentences. "
        "Do not use bullet lists or markdown headings. "
        f"Reply language mode: {language}. Operator message: {message}"
    )
    timeout_seconds = int(runtime_value("ORCHESTRATOR_LLM_TIMEOUT_SECONDS", "8"))
    if api_style == "openai_compatible":
        payload = json.dumps(
            {
                "model": model,
                "input": prompt,
                "max_output_tokens": 220,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(
            f"{base_url}/v1/responses",
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None
        output_text = body.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            answer = _strip_hidden_reasoning(output_text)
            return _sentence_safe_trim(answer) if answer else None
        output_items = body.get("output", [])
        if isinstance(output_items, list):
            collected: list[str] = []
            for item in output_items:
                if not isinstance(item, dict):
                    continue
                content_items = item.get("content", [])
                if not isinstance(content_items, list):
                    continue
                for content in content_items:
                    if isinstance(content, dict) and content.get("type") == "output_text":
                        text = str(content.get("text", "")).strip()
                        if text:
                            collected.append(text)
            if collected:
                answer = _strip_hidden_reasoning(" ".join(collected))
                return _sentence_safe_trim(answer) if answer else None
        return None

    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 110},
        }
    ).encode()
    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    answer = _strip_hidden_reasoning(str(body.get("response", "")))
    if not answer:
        return None
    return _sentence_safe_trim(answer)


def _is_recent_duplicate(session_id: str, safe_message: str, stream_name: str) -> bool:
    event_log = _event_log_path()
    if not event_log.exists():
        return False
    now = time()
    for line in event_log.read_text(encoding="utf-8").splitlines()[-20:]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        metadata = event.get("metadata") or {}
        if (
            event.get("agent") == "Operator"
            and event.get("stream") == stream_name
            and event.get("summary") == safe_message
            and metadata.get("session_id") == session_id
            and now - float(metadata.get("timestamp_epoch", 0)) < 8
        ):
            return True
    return False


def _append_event(event: dict[str, Any]) -> Path:
    event_log = _event_log_path()
    event_log.parent.mkdir(parents=True, exist_ok=True)
    with event_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    push_event(event)
    return event_log


def _supporting_agent_events(message: str, language: str, session_id: str) -> list[dict[str, Any]]:
    lowered = message.lower()
    events: list[dict[str, Any]] = []
    if any(word in lowered for word in ("debate", "challenge", "compare", "should we")):
        events.extend(
            [
                {
                    "agent": "Strategy Agent",
                    "stream": "Debate Mode",
                    "summary": "From a strategy perspective, I can discuss the setup quality, but I will not promote a trade unless backtest, forward test, demo validation, and governance gates pass.",
                    "input_sources": ["Orchestrator Chat", "Strategy Registry"],
                    "result": "strategy_position_visible",
                    "confidence": 0.77,
                    "risk_status": "no_executable_signal",
                    "next_action": "Ask Risk Manager and Signal Reviewer to challenge the setup before approval.",
                    "metadata": {"session_id": session_id, "language": language, "message_type": "debate_mode"},
                    "timestamp": _timestamp(),
                    "contains_hidden_chain_of_thought": False,
                },
                {
                    "agent": "Risk Manager",
                    "stream": "Debate Mode",
                    "summary": "From a risk perspective, I will block anything that lacks account permission, strategy permission, loss-limit checks, fresh market data, and approval records.",
                    "input_sources": ["Risk Policy", "Execution Guard"],
                    "result": "risk_challenge_visible",
                    "confidence": 0.86,
                    "risk_status": "approval_gates_required",
                    "next_action": "Keep the discussion visible, but do not create an order request from debate alone.",
                    "metadata": {"session_id": session_id, "language": language, "message_type": "debate_mode"},
                    "timestamp": _timestamp(),
                    "contains_hidden_chain_of_thought": False,
                },
            ]
        )
    if any(word in lowered for word in ("improve", "upgrade", "roadmap", "system improvement", "complete prompt", "next step")):
        events.append(
            {
                "agent": "System Improvement Agent",
                "stream": "System Improvement Room",
                "summary": "I received the improvement request. I will compare it with the roadmap, identify the next safest dependency, and keep deployment, rollback, tests, and audit records in scope.",
                "input_sources": ["Roadmap Checklist", "Deployment Agent", "Security Review Agent"],
                "result": "improvement_task_triaged",
                "confidence": 0.82,
                "risk_status": "change_requires_test_and_rollback_path",
                "next_action": "Work from the top incomplete roadmap section unless a lower dependency is required first.",
                "metadata": {"session_id": session_id, "language": language, "message_type": "system_improvement_room"},
                "timestamp": _timestamp(),
                "contains_hidden_chain_of_thought": False,
            }
        )
    if any(word in lowered for word in ("strategy", "backtest", "forward test", "signal", "tuning")):
        events.append(
            {
                "agent": "Strategy Agent",
                "stream": "Strategy War Room",
                "summary": "I received the operator request. I will treat this as a strategy-governance task, not an executable trade signal.",
                "input_sources": ["Orchestrator Chat"],
                "result": "task_triaged",
                "confidence": 0.78,
                "risk_status": "no_execution_permission",
                "next_action": "Prepare strategy review context after the strategy registry and backtest adapters are wired.",
                "metadata": {"session_id": session_id, "language": language, "message_type": "agent_task_ack"},
                "timestamp": _timestamp(),
                "contains_hidden_chain_of_thought": False,
            }
        )
    if any(word in lowered for word in ("risk", "drawdown", "loss", "permission", "approve", "approval")):
        events.append(
            {
                "agent": "Risk Manager",
                "stream": "Account Routing Room",
                "summary": "I received the operator request. I will keep all execution blocked unless policy, account, strategy, and approval checks pass.",
                "input_sources": ["Orchestrator Chat", "Execution Guard policy"],
                "result": "risk_task_triaged",
                "confidence": 0.84,
                "risk_status": "execution_guarded_monitor_only",
                "next_action": "Use governed approval records before any demo or live execution workflow.",
                "metadata": {"session_id": session_id, "language": language, "message_type": "agent_task_ack"},
                "timestamp": _timestamp(),
                "contains_hidden_chain_of_thought": False,
            }
        )
    if any(word in lowered for word in ("mt5", "bridge", "symbol", "price", "candle", "tick", "eurusd", "xauusd")):
        events.append(
            {
                "agent": "Market Data Agent",
                "stream": "Live Chat View",
                "summary": "I received the operator request. I will use MT5 bridge data once the market adapter is fully wired into the control plane.",
                "input_sources": ["Orchestrator Chat", "MT5 Bridge"],
                "result": "market_task_triaged",
                "confidence": 0.8,
                "risk_status": "data_only_no_execution",
                "next_action": "Wire symbol/rates/ticks into the market worker and quality checker.",
                "metadata": {"session_id": session_id, "language": language, "message_type": "agent_task_ack"},
                "timestamp": _timestamp(),
                "contains_hidden_chain_of_thought": False,
            }
        )
    return events


def _orchestrator_reply(message: str, language: str) -> tuple[str, str, str, str | None, int]:
    started = perf_counter()
    mode = _normalized_provider_mode(runtime_value("ORCHESTRATOR_GENERAL_CHAT_MODE", "local"))
    lowered = message.lower()
    is_ms = language == "ms-MY"
    provider = "disabled"
    fallback_reason: str | None = None
    is_time_question = any(
        word in lowered
        for word in ("time", "date", "today", "now", "current time", "current date", "masa", "tarikh", "hari ini", "sekarang")
    )
    if is_time_question:
        if is_ms:
            summary = (
                f"Masa fx-control sekarang ialah {format_local()}. "
                "Semua paparan operator dan Agent Theater menggunakan zon masa GMT+8."
            )
            next_action = "Gunakan halaman Agent Theater dalam dashboard untuk bertanya status masa, sistem, risiko, atau agen."
        else:
            summary = (
                f"The current fx-control time is {format_local()}. "
                "Operator-facing API and Agent Theater messages are displayed in GMT+8 time."
            )
            next_action = "Use the Agent Theater page in the dashboard for time, system, risk, and agent questions."
    elif any(word in lowered for word in ("who are you", "what are you", "which llm", "what llm", "model are you", "jenis apa", "llm apa", "siapa kamu")):
        if is_ms:
            summary = (
                "Saya ialah Orchestrator Agent untuk Forex AI Control Tower. Saya bukan saluran execution; "
                "saya menyelaras status, agen, analisis, risiko, dan tugasan operator melalui workflow yang diaudit."
            )
            next_action = "Tanya status sistem, risiko, berita, MT5 bridge, strategi, atau bilik agen yang anda mahu lihat."
        else:
            summary = (
                "I am the Forex AI Control Tower Orchestrator Agent. I am not a direct execution channel; "
                "I coordinate system status, agents, analysis, risk, and operator tasks through audited governed workflows."
            )
            next_action = "Ask for system status, risk, news, MT5 bridge, strategy readiness, or a specific Agent Theater room."
    elif any(word in lowered for word in ("buy", "sell", "order", "trade", "execute", "live", "lot")):
        summary = (
            "I understand the trading request and I can coordinate the required agents, but chat is not a direct execution channel. "
            "The proper flow is Signal -> Strategy validation -> Risk Manager -> Account Router -> Execution Guard -> MT5 Bridge "
            "with order_check before order_send and manual/admin approval where required."
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
    elif any(word in lowered for word in ("risk", "drawdown", "loss", "approve", "approval")):
        summary = (
            "I queued this as a governed Risk Manager review. No trade, approval, or policy change is assumed from chat; "
            "the Risk Manager will use account state, risk policy, permissions, and Execution Guard rules before anything can move forward."
        )
        next_action = "Review the queued agent task and risk policy records in the Control Plane."
    elif any(word in lowered for word in ("news", "calendar", "fundamental")):
        summary = (
            "News analysis now uses the configured economic-calendar adapter. If the provider is disabled, stale, or has a high-impact event "
            "inside the halt window, news-sensitive trading stays blocked by design."
        )
        next_action = "Check /api/v1/news/status for provider freshness, upcoming high-impact events, and the current news halt decision."
    else:
        llm_answer = None
        retry_count = max(0, min(3, int(runtime_value("ORCHESTRATOR_LLM_RETRY_COUNT", "1"))))
        if mode == "local":
            provider = "local"
            for _ in range(retry_count + 1):
                llm_answer = _ask_local_llm(message, language)
                if llm_answer:
                    break
            if llm_answer is None:
                fallback_reason = "local_unavailable_or_timeout"
        if mode == "disabled":
            provider = "disabled"
            summary = (
                "AI provider mode is disabled. I can still support system checks, safe routing, logs, and workflow guidance without LLM calls."
            )
            next_action = "Enable provider mode local when AI-generated responses are required."
        elif llm_answer is None:
            raise RuntimeError(PROVIDER_FAILURE_MESSAGE)
        else:
            summary = llm_answer
            next_action = "Ask a general question, request a system task, or ask me to route work to a specific agent."
    if is_ms and not is_time_question and provider == "disabled":
        summary = (
            "Saya terima mesej anda. Saya boleh bantu semak status sistem, risiko, agen, dan langkah seterusnya "
            "dalam bentuk ringkasan selamat. Saya tidak akan melangkaui kelulusan admin, Risk Manager, atau Execution Guard."
        )
        next_action = "Nyatakan bahagian yang anda mahu semak: kesihatan sistem, MT5 bridge, strategi, risiko, notifikasi, atau agen."
    latency_ms = int((perf_counter() - started) * 1000)
    return summary, next_action, provider, fallback_reason, latency_ms


def _audit_chat(action: str, session_id: str, details: dict[str, Any]) -> None:
    db: Session = SessionLocal()
    try:
        audit(db, None, action, "orchestrator_chat", session_id, details)
        db.commit()
    finally:
        db.close()


def _agent_for_message(message: str) -> tuple[str, str]:
    lowered = message.lower()
    if any(word in lowered for word in ("strategy", "backtest", "signal", "tuning")):
        return "Strategy Agent", "strategy_request"
    if any(word in lowered for word in ("risk", "drawdown", "loss", "approve", "approval")):
        return "Risk Manager", "risk_review"
    if any(word in lowered for word in ("mt5", "bridge", "symbol", "price", "candle", "tick", "eurusd", "xauusd")):
        return "Market Data Agent", "market_data_review"
    if any(word in lowered for word in ("deploy", "rollback", "backup", "service", "server")):
        return "Deployment Agent", "deployment_review"
    return "Orchestrator Agent", "operator_request"


def _queue_agent_task(session_id: str, message: str, language: str) -> str:
    assigned_agent, task_type = _agent_for_message(message)
    task_id = f"task_{secrets.token_hex(8)}"
    db: Session = SessionLocal()
    try:
        db.add(
            AgentTask(
                task_id=task_id,
                requested_by="operator_chat",
                assigned_agent=assigned_agent,
                task_type=task_type,
                priority=5,
                request_json={"session_id": session_id, "message": _safe_chat_text(message), "language": language},
                status="queued",
            )
        )
        audit(db, None, "queue", "agent_task", task_id, {"assigned_agent": assigned_agent, "task_type": task_type})
        db.commit()
        return task_id
    finally:
        db.close()


def _provider_status() -> dict[str, Any]:
    mode = _normalized_provider_mode(runtime_value("ORCHESTRATOR_GENERAL_CHAT_MODE", "local"))
    ollama_url = runtime_value("OLLAMA_REASON_URL", "http://10.10.1.82:11434").rstrip("/")
    local_model = runtime_value("ORCHESTRATOR_GENERAL_CHAT_MODEL", "llama3.1:8b")
    local_api_style = runtime_value("LOCAL_LLM_API_STYLE", "ollama").lower()
    ollama_ready = False
    try:
        health_path = "/v1/models" if local_api_style == "openai_compatible" else "/api/tags"
        request = urllib.request.Request(f"{ollama_url}{health_path}", method="GET")
        timeout_seconds = max(2, min(10, int(runtime_value("ORCHESTRATOR_LLM_TIMEOUT_SECONDS", "8"))))
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            ollama_ready = 200 <= response.status < 400
    except Exception:
        ollama_ready = False
    if mode == "local":
        active = "local" if ollama_ready else "unavailable"
    elif mode == "disabled":
        active = "disabled"
    else:
        active = "local" if ollama_ready else "unavailable"
    return {
        "mode": mode,
        "active_provider": active,
        "providers": {
            "local": {
                "configured": bool(ollama_url),
                "status": "ready" if ollama_ready else "unreachable",
                "url": ollama_url,
                "model": local_model,
                "api_style": local_api_style,
            },
            "disabled": {"configured": True, "status": "ready"},
        },
        "last_provider": _ORCHESTRATOR_RUNTIME.get("last_provider", "disabled"),
        "last_latency_ms": _ORCHESTRATOR_RUNTIME.get("last_latency_ms"),
    }


@router.get("/events")
def list_events(
    limit: int = 50,
    language: str = "en",
    stream: str | None = None,
    agent: list[str] | None = Query(default=None),
) -> dict:
    event_log = _event_log_path()
    if not event_log.exists():
        return {"events": [], "source": str(event_log), "modes": mode_names(), "agents": [], "streams": []}
    lines = event_log.read_text(encoding="utf-8").splitlines()[-500:]
    events = []
    agents = set()
    streams = set()
    selected_agents = set(agent or [])
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("agent"):
            agents.add(str(event["agent"]))
        if event.get("stream"):
            streams.add(str(event["stream"]))
        if stream and event.get("stream") != stream:
            continue
        if selected_agents and event.get("agent") not in selected_agents:
            continue
        events.append(event)
    deduped_reversed = []
    seen = set()
    for event in reversed(events):
        key = (event.get("agent"), event.get("stream"), event.get("summary"), event.get("result"), event.get("risk_status"))
        if key in seen:
            continue
        seen.add(key)
        deduped_reversed.append(event)
    events = list(reversed(deduped_reversed))[-max(1, min(limit, 200)) :]
    return {
        "events": render_events(events, language),
        "source": str(event_log),
        "modes": mode_names(),
        "agents": sorted(agents),
        "streams": sorted(streams),
    }


@router.get("/orchestrator/health")
def orchestrator_health() -> dict[str, Any]:
    provider = _provider_status()
    return {
        "status": "degraded" if _ORCHESTRATOR_RUNTIME.get("last_failed_reason") else "online",
        "provider": provider,
        "last_success_at": _ORCHESTRATOR_RUNTIME.get("last_success_at"),
        "last_failed_at": _ORCHESTRATOR_RUNTIME.get("last_failed_at"),
        "last_failed_reason": _ORCHESTRATOR_RUNTIME.get("last_failed_reason", ""),
        "last_provider": _ORCHESTRATOR_RUNTIME.get("last_provider", "static"),
        "last_latency_ms": _ORCHESTRATOR_RUNTIME.get("last_latency_ms"),
    }


@router.get("/console", response_class=HTMLResponse)
def orchestrator_console() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Orchestrator Console</title>
  <style>
    :root { color-scheme: dark; --bg:#0d1117; --panel:#161b22; --line:#21262d; --text:#e6edf3; --muted:#8b949e; --accent:#1f6feb; --accent2:#238636; --operator:#0d2818; --orch:#0d1b2a; --border:#30363d; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font: 14px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; }
    .app { display: flex; flex-direction: column; height: 100vh; height: 100dvh; }
    .topbar { background: var(--panel); border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; padding: 10px 16px; flex-shrink: 0; }
    .topbar h1 { font-size: 16px; font-weight: 600; white-space: nowrap; }
    .topbar .badge { background: var(--accent2); color: #fff; border-radius: 999px; font-size: 11px; font-weight: 600; padding: 2px 8px; }
    .topbar .spacer { flex: 1; }
    .topbar .status-pill { background: #161b22; border: 1px solid var(--border); border-radius: 999px; color: var(--muted); font-size: 12px; padding: 4px 10px; display: flex; align-items: center; gap: 6px; }
    .topbar .status-pill .dot { width: 7px; height: 7px; border-radius: 50%; }
    .topbar .status-pill .dot.ok { background: var(--accent2); }
    .topbar .status-pill .dot.warn { background: #d29922; }
    .topbar .status-pill .dot.err { background: #f85149; }
    .main { display: flex; flex: 1; min-height: 0; }
    .sidebar { background: var(--panel); border-right: 1px solid var(--border); display: flex; flex-direction: column; gap: 10px; padding: 14px; width: 340px; min-width: 280px; overflow-y: auto; flex-shrink: 0; }
    .sidebar h2 { font-size: 14px; font-weight: 600; }
    .sidebar p { color: var(--muted); font-size: 12px; line-height: 1.4; }
    .sidebar label { color: var(--muted); display: flex; flex-direction: column; gap: 4px; font-size: 12px; }
    .sidebar select, .sidebar textarea { background: #0d1117; border: 1px solid var(--border); border-radius: 6px; color: var(--text); font: inherit; padding: 8px 10px; width: 100%; }
    .sidebar textarea { min-height: 100px; resize: vertical; }
    .sidebar select:focus, .sidebar textarea:focus { border-color: var(--accent); outline: none; }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; }
    .chips button { background: #21262d; border: 1px solid var(--border); border-radius: 6px; color: var(--text); cursor: pointer; font-size: 12px; padding: 6px 10px; text-align: left; transition: background 0.15s; }
    .chips button:hover { background: #30363d; }
    .btn-send { background: var(--accent); border: none; border-radius: 6px; color: #fff; cursor: pointer; font-weight: 600; padding: 10px; text-align: center; transition: background 0.15s; width: 100%; }
    .btn-send:hover { background: #388bfd; }
    .btn-send:disabled { opacity: 0.5; cursor: not-allowed; }
    .feed-area { display: flex; flex-direction: column; flex: 1; min-width: 0; }
    .feed-header { background: var(--panel); border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 10px; padding: 8px 16px; flex-shrink: 0; }
    .feed-header span { color: var(--muted); font-size: 12px; }
    .feed-header .refresh-ctrl { margin-left: auto; display: flex; align-items: center; gap: 6px; }
    .feed-header select { background: #0d1117; border: 1px solid var(--border); border-radius: 4px; color: var(--text); font-size: 12px; padding: 3px 6px; }
    .feed { display: flex; flex-direction: column; gap: 0; flex: 1; overflow-y: auto; padding: 0; }
    .msg { border-bottom: 1px solid var(--border); display: grid; grid-template-columns: 140px 1fr auto; gap: 10px; padding: 10px 16px; transition: background 0.15s; }
    .msg:hover { background: #161b22; }
    .msg.operator { background: var(--operator); }
    .msg.orchestrator { background: var(--orch); }
    .msg .agent { color: #58a6ff; font-weight: 600; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .msg .room { color: var(--muted); font-size: 11px; margin-top: 2px; }
    .msg .body { font-size: 13px; line-height: 1.4; }
    .msg .body .next { color: var(--muted); font-size: 12px; margin-top: 4px; }
    .msg .meta { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; min-width: 100px; }
    .msg .meta .time { color: var(--muted); font-size: 11px; white-space: nowrap; }
    .msg .meta .tags { display: flex; flex-wrap: wrap; gap: 4px; justify-content: flex-end; }
    .msg .meta .tags span { border-radius: 999px; font-size: 10px; padding: 2px 6px; }
    .msg .meta .tags .ok { background: #0d2818; border: 1px solid #1f6feb33; color: #7ee787; }
    .msg .meta .tags .warn { background: #2d1f00; border: 1px solid #d2992233; color: #d29922; }
    .msg .meta .tags .bad { background: #2d0a0a; border: 1px solid #f8514933; color: #f85149; }
    .msg .meta .tags .neutral { background: #161b22; border: 1px solid var(--border); color: var(--muted); }
    .empty { color: var(--muted); padding: 40px; text-align: center; }
    .status-bar { background: var(--panel); border-top: 1px solid var(--border); color: var(--muted); font-size: 12px; padding: 6px 16px; flex-shrink: 0; }
    @media (max-width: 768px) {
      .main { flex-direction: column; }
      .sidebar { width: 100%; border-right: none; border-bottom: 1px solid var(--border); max-height: 45vh; }
      .msg { grid-template-columns: 1fr; }
      .msg .meta { align-items: flex-start; flex-direction: row; }
      .msg .meta .tags { justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar">
      <h1>Orchestrator Console</h1>
      <span class="badge">Ollama</span>
      <div class="spacer"></div>
      <div class="status-pill" id="providerPill"><span class="dot ok" id="providerDot"></span><span id="providerLabel">Local LLM: checking...</span></div>
    </header>
    <div class="main">
      <aside class="sidebar">
        <h2>Talk To Orchestrator</h2>
        <p>Read-only governed chat. No trade execution or approval bypass. Powered by local Ollama LLM.</p>
        <form id="chatForm">
          <label>Language
            <select id="language"><option value="en">English</option><option value="ms-MY">Bahasa Melayu</option><option value="auto">Auto</option></select>
          </label>
          <label>Message
            <textarea id="message" placeholder="Ask about time, system status, risk, MT5 bridge, strategies, deployment..."></textarea>
          </label>
          <button class="btn-send" type="submit" id="sendBtn">Send To Orchestrator</button>
        </form>
        <div class="chips">
          <button type="button" data-prompt="What is the current time and date?">Time & Date</button>
          <button type="button" data-prompt="What is the full system status?">System Status</button>
          <button type="button" data-prompt="Summarize today risk posture for demo trading.">Risk Posture</button>
          <button type="button" data-prompt="What is blocking demo trading activation?">Demo Blockers</button>
          <button type="button" data-prompt="Explain how this control tower operates safely.">How It Works</button>
        </div>
      </aside>
      <div class="feed-area">
        <div class="feed-header">
          <span id="countLabel">0 messages</span>
          <span id="updatedLabel"></span>
          <div class="refresh-ctrl">
            <label style="color:var(--muted);font-size:12px;">Refresh
              <select id="refreshRate">
                <option value="1000">1s</option>
                <option value="2000" selected>2s</option>
                <option value="5000">5s</option>
                <option value="10000">10s</option>
                <option value="0">Paused</option>
              </select>
            </label>
            <button type="button" id="refreshNow" style="background:#21262d;border:1px solid var(--border);border-radius:4px;color:var(--text);cursor:pointer;font-size:12px;padding:3px 8px;">Refresh</button>
          </div>
        </div>
        <div class="feed" id="feed"></div>
      </div>
    </div>
    <div class="status-bar" id="statusBar">Ready. Chat cannot bypass approvals, Risk Manager, or Execution Guard.</div>
  </div>
  <script>
    const apiBase = window.location.origin;
    const feed = document.getElementById('feed');
    const statusBar = document.getElementById('statusBar');
    const messageEl = document.getElementById('message');
    const languageEl = document.getElementById('language');
    const countLabel = document.getElementById('countLabel');
    const updatedLabel = document.getElementById('updatedLabel');
    const providerDot = document.getElementById('providerDot');
    const providerLabel = document.getElementById('providerLabel');
    let events = [];
    let refreshTimer = null;

    function esc(v) { return String(v||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
    function riskClass(r) { const s=String(r||'').toLowerCase(); return s.includes('blocked')||s.includes('halt')||s.includes('safe_mode')?'bad':s.includes('waiting')||s.includes('manual')||s.includes('review')?'warn':'ok'; }

    function render() {
      countLabel.textContent = events.length + ' messages';
      if (!events.length) { feed.innerHTML = '<div class="empty">No orchestrator messages yet.</div>'; return; }
      feed.innerHTML = events.slice(-80).reverse().map(e => {
        const isOp = e.agent === 'Operator';
        const agent = e.agent === 'Orchestrator Agent' ? 'Orchestrator' : (e.agent || 'Agent');
        const risk = e.display?.risk_status || e.risk_status || 'read_only';
        const rc = riskClass(risk);
        return `<article class="msg ${isOp?'operator':'orchestrator'}">
          <div><div class="agent" title="${esc(e.agent)}">${esc(agent)}</div><div class="room">${esc(e.stream||'Orchestrator Console')}</div></div>
          <div class="body"><div>${esc(e.display?.summary||e.summary||'No summary.')}</div>${e.next_action?`<div class="next">${esc(e.next_action)}</div>`:''}</div>
          <div class="meta"><div class="time">${esc(e.timestamp||'')}</div><div class="tags"><span class="${rc}">${esc(risk)}</span><span class="neutral">${esc(e.result||'safe_reply')}</span></div></div>
        </article>`;
      }).join('');
    }

    async function loadEvents() {
      try {
        const r = await fetch(`${apiBase}/api/v1/agent-theater/events?limit=40&stream=Orchestrator%20Console&agent=Operator&agent=Orchestrator%20Agent`, {headers:{'Accept':'application/json'}});
        const b = await r.json();
        events = b.events || [];
        render();
        updatedLabel.textContent = 'updated ' + new Date().toLocaleTimeString();
      } catch(e) { updatedLabel.textContent = 'refresh failed'; }
    }

    async function loadHealth() {
      try {
        const r = await fetch(`${apiBase}/api/v1/agent-theater/orchestrator/health`);
        const h = await r.json();
        const p = h.provider || {};
        const local = p.providers?.local || {};
        const ok = local.status === 'ready';
        providerDot.className = 'dot ' + (ok ? 'ok' : 'err');
        providerLabel.textContent = ok ? `Local LLM: ${local.model||'ollama'}` : 'Local LLM: unreachable';
      } catch(e) { providerDot.className = 'dot err'; providerLabel.textContent = 'Local LLM: error'; }
    }

    async function send(message) {
      statusBar.textContent = 'Sending to Orchestrator...';
      try {
        const r = await fetch(`${apiBase}/api/v1/agent-theater/chat`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({message, language: languageEl.value, session_id:'standalone-orchestrator-console', orchestrator_only:true})
        });
        const b = await r.json();
        if (!r.ok) throw new Error(b.detail||'Chat failed');
        const lat = Number.isFinite(Number(b.latency_ms)) ? ` in ${b.latency_ms}ms` : '';
        statusBar.textContent = `Orchestrator replied via ${b.provider||'local'}${lat}.`;
        await loadEvents();
      } catch(e) { statusBar.textContent = e.message || 'Unable to reach Orchestrator.'; }
    }

    document.querySelectorAll('[data-prompt]').forEach(b => b.addEventListener('click', () => { messageEl.value = b.dataset.prompt; messageEl.focus(); }));
    document.getElementById('chatForm').addEventListener('submit', e => { e.preventDefault(); const m=messageEl.value.trim(); if(!m)return; messageEl.value=''; send(m); });
    document.getElementById('refreshNow').addEventListener('click', () => loadEvents());
    document.getElementById('refreshRate').addEventListener('change', function() {
      if(refreshTimer) clearInterval(refreshTimer);
      const ms = Number(this.value);
      if(ms>0) refreshTimer = setInterval(loadEvents, ms);
    });
    loadEvents(); loadHealth();
    setInterval(loadHealth, 30000);
    const ws = new WebSocket(apiBase.replace(/^http/,'ws')+'/ws/v1/agent-theater');
    ws.onmessage = m => { try { events.push(JSON.parse(m.data)); render(); } catch(_){} };
  </script>
</body>
</html>
        """
    )


@router.post("/chat", status_code=status.HTTP_202_ACCEPTED)
def chat_with_orchestrator(
    payload: OrchestratorChatIn,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    if not _chat_allowed(request, authorization):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    safe_message = _safe_chat_text(payload.message)
    stream_name = "Orchestrator Console" if payload.orchestrator_only else "Orchestrator Chat"
    if _is_recent_duplicate(payload.session_id, safe_message, stream_name):
        return {"accepted": True, "duplicate_suppressed": True, "reply": "Duplicate message suppressed.", "next_action": "Wait for the existing orchestrator reply.", "task_id": None}
    task_id = f"chat_{secrets.token_hex(8)}" if payload.orchestrator_only else _queue_agent_task(payload.session_id, payload.message, payload.language)
    operator_event = {
        "agent": "Operator",
        "stream": stream_name,
        "summary": safe_message,
        "input_sources": ["Dashboard chat"],
        "result": "operator_message_received",
        "confidence": 1.0,
        "risk_status": "read_only_chat_no_execution",
        "next_action": "Orchestrator will answer with a safe status summary.",
        "metadata": {"session_id": payload.session_id, "language": payload.language, "message_type": "operator_chat", "task_id": task_id, "timestamp_epoch": time()},
        "timestamp": _timestamp(),
        "contains_hidden_chain_of_thought": False,
    }
    _append_event(redact(operator_event))

    try:
        reply, next_action, provider_used, fallback_reason, latency_ms = _orchestrator_reply(payload.message, payload.language)
        _ORCHESTRATOR_RUNTIME["last_success_at"] = _timestamp()
        _ORCHESTRATOR_RUNTIME["last_provider"] = provider_used
        _ORCHESTRATOR_RUNTIME["last_latency_ms"] = latency_ms
    except Exception as exc:
        _ORCHESTRATOR_RUNTIME["last_failed_at"] = _timestamp()
        message = str(exc) if str(exc).strip() else f"{type(exc).__name__}: orchestrator_reply_failed"
        _ORCHESTRATOR_RUNTIME["last_failed_reason"] = message
        _audit_chat(
            "orchestrator_chat_failed",
            payload.session_id,
            {"error": type(exc).__name__, "message": message, "language": payload.language, "orchestrator_only": payload.orchestrator_only},
        )
        if PROVIDER_FAILURE_MESSAGE in message:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=PROVIDER_FAILURE_MESSAGE) from exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Orchestrator is temporarily unavailable. Please retry.") from exc
    if not payload.orchestrator_only:
        for agent_event in _supporting_agent_events(payload.message, payload.language, payload.session_id):
            _append_event(redact(agent_event))
    orchestrator_event = {
        "agent": "Orchestrator Agent",
        "stream": stream_name,
        "summary": reply,
        "input_sources": ["Control plane status", "Execution Guard policy", "Agent Theater"],
        "result": "safe_reply",
        "confidence": 0.86,
        "risk_status": "read_only_no_trade_execution",
        "next_action": next_action,
        "metadata": {
            "session_id": payload.session_id,
            "language": payload.language,
            "message_type": "orchestrator_reply",
            "task_id": task_id,
            "provider": provider_used,
            "fallback_reason": fallback_reason,
            "latency_ms": latency_ms,
        },
        "timestamp": _timestamp(),
        "contains_hidden_chain_of_thought": False,
    }
    _append_event(redact(orchestrator_event))
    _audit_chat(
        "orchestrator_chat",
        payload.session_id,
        {
            "language": payload.language,
            "message_redacted": safe_message != " ".join(payload.message.strip().split()),
            "orchestrator_only": payload.orchestrator_only,
        },
    )
    return {
        "accepted": True,
        "reply": reply,
        "next_action": next_action,
        "task_id": task_id,
        "provider": provider_used,
        "fallback_reason": fallback_reason,
        "latency_ms": latency_ms,
    }


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


@router.post("/rooms/{room_name}/seed", status_code=status.HTTP_202_ACCEPTED)
def seed_room_status(
    room_name: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    if room_name not in mode_names():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown Agent Theater room")
    if not _chat_allowed(request, authorization):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    events = room_seed_events(room_name)
    for event in events:
        _append_event(redact(event))
    return {"accepted": True, "events": [render_event(event) for event in events]}

