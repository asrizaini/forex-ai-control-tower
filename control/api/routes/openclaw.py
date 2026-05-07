from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid
import urllib.error
import urllib.request
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import AgentTask, NotificationEvent, SignalRecord, TradingPair, WorkerStatus
from ..time_utils import utcnow, format_local
from localization.locale_manager import normalize_language
from openclaw_gateway.api_bridge import (
    ALLOWED_ACTIONS,
    FORBIDDEN_ACTIONS,
    action_allowed,
    call_openclaw_runtime,
    can_execute_trade,
    openclaw_enabled,
    probe_openclaw_runtime_health,
    openclaw_status,
)

router = APIRouter(prefix="/openclaw", tags=["openclaw"])

ALLOWED_STATUS_QUERY_TARGETS = {
    "system",
    "risk",
    "signals",
    "workers",
    "news",
    "accounts",
    "pairs",
}

ALLOWED_APPROVED_API_PATHS = {
    "/api/v1/system/runtime",
    "/api/v1/system/health/status",
    "/api/v1/workers/status",
    "/api/v1/news/status",
    "/api/v1/calendar/status",
    "/api/v1/signals/summary",
    "/api/v1/pair-summaries",
}


class OpenClawActionRequest(BaseModel):
    action: str = Field(max_length=120)
    approved: bool = False
    message: str = Field(default="", max_length=1000)


class OpenClawChatRequest(BaseModel):
    role: str = Field(default="user", pattern="^(admin|user)$")
    message: str = Field(min_length=1, max_length=1200)
    language: str = Field(default="en", max_length=16)


class OpenClawStatusQueryRequest(BaseModel):
    target: str = Field(default="system", max_length=80)
    language: str = Field(default="en", max_length=16)


class OpenClawDailySummaryRequest(BaseModel):
    language: str = Field(default="en", max_length=16)


class OpenClawApprovedApiCallRequest(BaseModel):
    path: str = Field(max_length=200)
    approved: bool = True
    reason: str = Field(default="", max_length=300)


def _safe_summary_for_target(db: Session, target: str, language: str) -> str:
    normalized = normalize_language(language)
    time_marker = format_local(utcnow())
    enabled_pairs = db.scalar(select(func.count()).select_from(TradingPair).where(TradingPair.enabled.is_(True))) or 0
    worker_running = db.scalar(select(func.count()).select_from(WorkerStatus).where(WorkerStatus.status == "running")) or 0
    pending_tasks = db.scalar(select(func.count()).select_from(AgentTask).where(AgentTask.status == "queued")) or 0
    latest_signals = db.scalar(select(func.count()).select_from(SignalRecord)) or 0
    notifications_sent = db.scalar(
        select(func.count()).select_from(NotificationEvent).where(NotificationEvent.status.in_(["sent", "partial_delivery"]))
    ) or 0

    if normalized == "ms-MY":
        summaries = {
            "system": f"Ringkasan sistem pada {time_marker}: {worker_running} worker sedang berjalan, {pending_tasks} tugasan menunggu giliran.",
            "risk": "Mod risiko kekal terkawal: aliran dagangan automatik masih tertakluk kepada Execution Guard dan kelulusan.",
            "signals": f"Isyarat semasa dipantau untuk {enabled_pairs} pair aktif dengan {latest_signals} rekod isyarat tersimpan.",
            "workers": f"Terdapat {worker_running} worker berstatus running dan queue tugasan semasa ialah {pending_tasks}.",
            "news": "Saluran berita/fundamental aktif; keputusan dagangan kekal berpagar apabila tingkap impak tinggi aktif.",
            "accounts": "Ringkasan akaun memerlukan semakan dashboard; OpenClaw tidak boleh menghantar arahan dagangan.",
            "pairs": f"{enabled_pairs} pair diaktifkan untuk analisis. Pair yang dinyahaktif tidak diproses oleh worker.",
        }
        return summaries.get(target, summaries["system"])

    summaries = {
        "system": f"System summary at {time_marker}: {worker_running} workers running and {pending_tasks} queued agent tasks.",
        "risk": "Risk posture is guarded: auto-trading remains gated by Execution Guard, policy checks, and approvals.",
        "signals": f"Signal layer is monitoring {enabled_pairs} enabled pairs with {latest_signals} persisted signal records.",
        "workers": f"Worker runtime currently has {worker_running} running workers and {pending_tasks} queued tasks.",
        "news": "News/fundamental adapter is active; signal routing remains blocked during high-impact windows.",
        "accounts": "Account-level details remain dashboard-governed; OpenClaw cannot place or modify trades.",
        "pairs": f"{enabled_pairs} trading pairs are enabled for analysis. Disabled pairs are safely skipped.",
    }
    return summaries.get(target, summaries["system"])


def _daily_summary(db: Session, language: str) -> str:
    normalized = normalize_language(language)
    enabled_pairs = db.scalar(select(func.count()).select_from(TradingPair).where(TradingPair.enabled.is_(True))) or 0
    workers_running = db.scalar(select(func.count()).select_from(WorkerStatus).where(WorkerStatus.status == "running")) or 0
    latest_signals = db.scalar(select(func.count()).select_from(SignalRecord)) or 0
    notifications_sent = db.scalar(
        select(func.count()).select_from(NotificationEvent).where(NotificationEvent.status.in_(["sent", "partial_delivery"]))
    ) or 0

    if normalized == "ms-MY":
        return (
            f"Ringkasan harian: {enabled_pairs} pair aktif, {workers_running} worker berjalan, "
            f"{latest_signals} rekod isyarat, dan {notifications_sent} notifikasi telah dihantar. "
            "Sistem kekal dalam mod kawalan selamat; tiada pelaksanaan dagangan terus oleh OpenClaw."
        )
    return (
        f"Daily summary: {enabled_pairs} enabled pairs, {workers_running} running workers, "
        f"{latest_signals} signal records, and {notifications_sent} sent notifications. "
        "System remains in governed safe mode; OpenClaw has no direct trade execution path."
    )


@router.get("")
def list_resource() -> dict:
    status = openclaw_status()
    return {
        "module": "openclaw",
        "description": "Optional OpenClaw gateway, disabled by default and restricted to human-facing workflows.",
        "mode": "production-required",
        **status,
    }


@router.get("/status")
def gateway_status() -> dict:
    status = openclaw_status()
    return {
        **status,
        "safe_mode": True,
        "runtime_bridge_state": "active" if status["enabled"] and status["runtime_configured"] else "local_safe_fallback",
    }


@router.get("/runtime/health")
def runtime_health() -> dict:
    status = openclaw_status()
    probe = probe_openclaw_runtime_health()
    return {
        **status,
        "runtime_probe": probe,
        "runtime_bridge_state": "active" if probe.get("ok") else "degraded",
        "safe_mode": True,
    }


@router.get("/contract")
def openclaw_contract() -> dict:
    return {
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "forbidden_actions": sorted(FORBIDDEN_ACTIONS),
        "allowed_status_query_targets": sorted(ALLOWED_STATUS_QUERY_TARGETS),
        "allowed_approved_api_paths": sorted(ALLOWED_APPROVED_API_PATHS),
        "execution_capability": "disabled",
        "notes": "OpenClaw remains human-facing only and cannot bypass governance or execute trades.",
    }


@router.post("/actions/check")
def check_action(payload: OpenClawActionRequest, principal: Principal = Depends(current_principal)) -> dict:
    allowed, reason = action_allowed(payload.action, payload.approved)
    return {
        "action": payload.action,
        "allowed": allowed,
        "reason": reason,
        "actor": principal.user_id,
        "trade_execution_allowed": False,
        "safe_summary": "OpenClaw may assist with approved human-facing API workflows only; it cannot execute trades or bypass governance.",
    }


@router.post("/chat")
def chat(payload: OpenClawChatRequest, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> dict:
    action = "admin_chat" if payload.role == "admin" else "user_chat"
    allowed, reason = action_allowed(action, approved=True)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    message = payload.message.strip()
    language = normalize_language(payload.language)
    reply = _safe_summary_for_target(db, "system", language)
    external = False
    runtime_result: dict[str, Any] = {}
    if openclaw_enabled():
        runtime_result = call_openclaw_runtime(
            "/chat",
            {
                "session_id": f"openclaw_{uuid.uuid4().hex[:10]}",
                "role": payload.role,
                "language": language,
                "message": message,
            },
        )
        if runtime_result.get("ok"):
            external = True
            raw = runtime_result.get("raw", "")
            reply = raw[:1000] if isinstance(raw, str) and raw else reply

    audit(
        db,
        principal,
        "openclaw_chat",
        "openclaw_gateway",
        action,
        {"role": payload.role, "language": language, "message_length": len(message), "external_runtime": external},
    )
    db.commit()
    return {
        "ok": True,
        "action": action,
        "language": language,
        "external_runtime": external,
        "reply": reply,
        "trade_execution_allowed": False,
        "reason": "safe_human_facing_response",
    }


@router.post("/status/query")
def status_query(payload: OpenClawStatusQueryRequest, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> dict:
    action = "status_queries"
    allowed, reason = action_allowed(action, approved=True)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)
    target = payload.target.strip().lower()
    if target not in ALLOWED_STATUS_QUERY_TARGETS:
        raise HTTPException(status_code=400, detail="Unsupported status query target")

    language = normalize_language(payload.language)
    summary = _safe_summary_for_target(db, target, language)
    audit(db, principal, "openclaw_status_query", "openclaw_gateway", target, {"language": language})
    db.commit()
    return {
        "ok": True,
        "target": target,
        "language": language,
        "summary": summary,
        "trade_execution_allowed": False,
    }


@router.post("/summary/daily")
def daily_summary(payload: OpenClawDailySummaryRequest, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> dict:
    action = "daily_summaries"
    allowed, reason = action_allowed(action, approved=True)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)
    language = normalize_language(payload.language)
    summary = _daily_summary(db, language)
    audit(db, principal, "openclaw_daily_summary", "openclaw_gateway", "daily", {"language": language})
    db.commit()
    return {
        "ok": True,
        "language": language,
        "summary": summary,
        "trade_execution_allowed": False,
    }


@router.post("/api-call")
def approved_api_call(
    payload: OpenClawApprovedApiCallRequest,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> dict:
    if principal.role != "super_admin":
        raise HTTPException(status_code=403, detail="super_admin required")
    allowed, reason = action_allowed("approved_api_calls", payload.approved)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)
    if payload.path not in ALLOWED_APPROVED_API_PATHS:
        raise HTTPException(status_code=400, detail="path not allowed")

    endpoint = f"http://127.0.0.1:8000{payload.path}"
    proxied: dict[str, Any]
    try:
        request = urllib.request.Request(endpoint, headers={"Accept": "application/json"}, method="GET")
        with urllib.request.urlopen(request, timeout=6) as response:
            raw = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else {}
            proxied = {"status_code": response.status, "data": parsed}
    except urllib.error.HTTPError as exc:
        proxied = {"status_code": exc.code, "data": {"detail": "upstream_error"}}
    except Exception as exc:
        proxied = {"status_code": 503, "data": {"detail": type(exc).__name__}}

    audit(
        db,
        principal,
        "openclaw_approved_api_call",
        "openclaw_gateway",
        payload.path,
        {"approved": True, "reason": payload.reason[:180], "status_code": proxied["status_code"]},
    )
    db.commit()
    return {
        "ok": True,
        "path": payload.path,
        "allowed": True,
        "upstream": proxied,
        "trade_execution_allowed": False,
        "note": "Only approved read-only API bridge paths are permitted.",
    }
