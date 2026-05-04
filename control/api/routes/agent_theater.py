from __future__ import annotations

import json
import os
import re
import secrets
import urllib.error
import urllib.request
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import decode_token
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
    if os.getenv("ORCHESTRATOR_GENERAL_CHAT_MODE", "static").lower() != "ollama":
        return None
    base_url = os.getenv("OLLAMA_REASON_URL", "http://10.10.1.82:11434").rstrip("/")
    model = os.getenv("ORCHESTRATOR_GENERAL_CHAT_MODEL", "llama3.1:8b")
    prompt = (
        "You are the Forex AI Control Tower Orchestrator, a safe human-facing assistant. "
        "Answer general questions naturally and helpfully. For trading, deployment, credentials, or system actions, "
        "explain the governed workflow and never claim an unsafe action was executed. Do not reveal hidden reasoning. "
        "Do not ask for or repeat secrets. The Control Tower principle is: AI analyzes, Risk engine controls, "
        "Admin approves, MT5 executes. You do not execute trades yourself. Answer in 3 to 5 short sentences. "
        "Do not use bullet lists or markdown headings. "
        f"Reply language mode: {language}. Operator message: {message}"
    )
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
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    answer = _strip_hidden_reasoning(str(body.get("response", "")))
    if not answer:
        return None
    return _sentence_safe_trim(answer)


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


def _orchestrator_reply(message: str, language: str) -> tuple[str, str]:
    lowered = message.lower()
    is_ms = language == "ms-MY"
    is_time_question = any(
        word in lowered
        for word in ("time", "date", "today", "now", "current time", "current date", "masa", "tarikh", "hari ini", "sekarang")
    )
    if is_time_question:
        if is_ms:
            summary = (
                f"Masa fx-control sekarang ialah {format_local()}. "
                "Semua paparan operator dan Agent Theater akan menggunakan zon masa Asia/Kuala_Lumpur."
            )
            next_action = "Gunakan halaman Agent Theater dalam dashboard untuk bertanya status masa, sistem, risiko, atau agen."
        else:
            summary = (
                f"The current fx-control time is {format_local()}. "
                "Operator-facing API and Agent Theater messages are displayed in Asia/Kuala_Lumpur time."
            )
            next_action = "Use the Agent Theater page in the dashboard for time, system, risk, and agent questions."
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
        llm_answer = _ask_local_llm(message, language)
        summary = llm_answer or (
            "I received your message. I can handle general questions, planning, explanations, operator requests, and safe task routing. "
            "For trading or infrastructure actions, I will coordinate the relevant agent and keep governance, audit, and approval gates in place."
        )
        next_action = "Ask a general question, request a system task, or ask me to route work to a specific agent."
    if is_ms and not is_time_question:
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
    events = events[-max(1, min(limit, 200)) :]
    return {
        "events": render_events(events, language),
        "source": str(event_log),
        "modes": mode_names(),
        "agents": sorted(agents),
        "streams": sorted(streams),
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
    :root { color-scheme: dark; --bg:#11161c; --panel:#171d24; --line:#29323d; --text:#e7edf5; --muted:#9aa7b7; --accent:#18a88b; --operator:#17352f; }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.45 Inter, ui-sans-serif, system-ui, sans-serif; }
    .wrap { display: grid; grid-template-columns: minmax(280px, 380px) minmax(0, 1fr); gap: 12px; height: 100vh; padding: 12px; }
    .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; min-height: 0; }
    .composer { padding: 14px; }
    h1 { font-size: 17px; margin: 0 0 4px; }
    p { color: var(--muted); margin: 0; }
    .chips { display: grid; gap: 8px; margin: 14px 0; }
    button { border: 1px solid var(--line); border-radius: 6px; background: #202832; color: var(--text); cursor: pointer; padding: 9px 10px; text-align: left; }
    button.primary { align-items: center; background: var(--accent); border: 0; color: #031b16; display: flex; font-weight: 700; justify-content: center; text-align: center; }
    select, textarea { width: 100%; border: 1px solid var(--line); border-radius: 6px; background: #0f141a; color: var(--text); font: inherit; padding: 10px; }
    textarea { min-height: 126px; resize: vertical; }
    label { color: var(--muted); display: grid; gap: 6px; margin-bottom: 10px; }
    .status { color: var(--muted); font-size: 12px; margin-top: 10px; }
    .feed { display: grid; gap: 10px; max-height: calc(100vh - 24px); overflow: auto; padding: 12px; }
    .msg { background: #111820; border: 1px solid var(--line); border-radius: 8px; padding: 12px; }
    .msg.operator { background: var(--operator); }
    .top { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 6px; }
    .top strong { color: #7ee2ce; }
    .top span { color: var(--muted); font-size: 12px; white-space: nowrap; }
    .meta { color: var(--muted); display: flex; flex-wrap: wrap; gap: 8px; font-size: 12px; margin-top: 9px; }
    .meta span { border: 1px solid var(--line); border-radius: 999px; padding: 3px 7px; }
    @media (max-width: 820px) { .wrap { grid-template-columns: 1fr; height: auto; } .feed { max-height: 68vh; } }
  </style>
</head>
<body>
  <main class="wrap">
    <section class="panel composer">
      <h1>Orchestrator Console</h1>
      <p>Talk to the Control Tower. Requests are audited and routed through safe agent workflows.</p>
      <div class="chips">
        <button type="button" data-prompt="What is the full system status and what should we do next?">Full status</button>
        <button type="button" data-prompt="Check MT5 bridge readiness and route this to the market data agent.">MT5 readiness</button>
        <button type="button" data-prompt="Explain what is blocking demo trading activation.">Demo trading blockers</button>
        <button type="button" data-prompt="I need a general explanation of how this control tower should operate.">General explanation</button>
      </div>
      <form id="chatForm">
        <label>Language
          <select id="language"><option value="en">English</option><option value="ms-MY">Bahasa Melayu Malaysia</option><option value="auto">Auto</option></select>
        </label>
        <label>Message
          <textarea id="message" placeholder="Ask anything: general questions, system tasks, trading workflow, MT5 bridge, risk, strategy, notifications, deployment..."></textarea>
        </label>
        <button class="primary" type="submit">Send To Orchestrator</button>
      </form>
      <div class="status" id="status">Ready. Chat cannot bypass approvals, Risk Manager, or Execution Guard.</div>
    </section>
    <section class="panel feed" id="feed"></section>
  </main>
  <script>
    const apiBase = window.location.origin;
    const wsBase = apiBase.replace(/^http/, 'ws');
    const feed = document.getElementById('feed');
    const statusEl = document.getElementById('status');
    const messageEl = document.getElementById('message');
    const languageEl = document.getElementById('language');
    let events = [];

    function escapeHtml(value) {
      return String(value || '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    }

    function render() {
      feed.innerHTML = events.slice(-80).reverse().map((event) => `
        <article class="msg ${event.agent === 'Operator' ? 'operator' : ''}">
          <div class="top"><strong>${escapeHtml(event.agent)}</strong><span>${escapeHtml(event.stream)} - ${escapeHtml(event.timestamp || '')}</span></div>
          <div>${escapeHtml(event.summary)}</div>
          <div class="meta"><span>${escapeHtml(event.result)}</span><span>${escapeHtml(event.risk_status)}</span><span>${escapeHtml(event.next_action)}</span></div>
        </article>
      `).join('');
    }

    async function loadEvents() {
      const response = await fetch(`${apiBase}/api/v1/agent-theater/events?limit=40&stream=Orchestrator%20Console&agent=Operator&agent=Orchestrator%20Agent`);
      const body = await response.json();
      events = body.events || [];
      render();
    }

    async function send(message) {
      statusEl.textContent = 'Sending to Orchestrator...';
      const response = await fetch(`${apiBase}/api/v1/agent-theater/chat`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message, language: languageEl.value, session_id: 'standalone-orchestrator-console', orchestrator_only: true})
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Chat failed');
      statusEl.textContent = body.next_action || 'Orchestrator replied.';
      await loadEvents();
    }

    document.querySelectorAll('[data-prompt]').forEach((button) => {
      button.addEventListener('click', () => { messageEl.value = button.dataset.prompt; messageEl.focus(); });
    });
    document.getElementById('chatForm').addEventListener('submit', async (event) => {
      event.preventDefault();
      const message = messageEl.value.trim();
      if (!message) return;
      messageEl.value = '';
      try { await send(message); } catch (error) { statusEl.textContent = error.message || 'Unable to reach Orchestrator.'; }
    });

    loadEvents().catch(() => { statusEl.textContent = 'Waiting for Agent Theater events.'; });
    const ws = new WebSocket(`${wsBase}/ws/v1/agent-theater`);
    ws.onmessage = (message) => {
      try { events.push(JSON.parse(message.data)); render(); } catch (_) {}
    };
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
    task_id = _queue_agent_task(payload.session_id, payload.message, payload.language)
    stream_name = "Orchestrator Console" if payload.orchestrator_only else "Orchestrator Chat"
    operator_event = {
        "agent": "Operator",
        "stream": stream_name,
        "summary": safe_message,
        "input_sources": ["Dashboard chat"],
        "result": "operator_message_received",
        "confidence": 1.0,
        "risk_status": "read_only_chat_no_execution",
        "next_action": "Orchestrator will answer with a safe status summary.",
        "metadata": {"session_id": payload.session_id, "language": payload.language, "message_type": "operator_chat", "task_id": task_id},
        "timestamp": _timestamp(),
        "contains_hidden_chain_of_thought": False,
    }
    _append_event(redact(operator_event))

    reply, next_action = _orchestrator_reply(payload.message, payload.language)
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
        "metadata": {"session_id": payload.session_id, "language": payload.language, "message_type": "orchestrator_reply", "task_id": task_id},
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
    return {"accepted": True, "reply": reply, "next_action": next_action, "task_id": task_id}


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

