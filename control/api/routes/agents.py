from __future__ import annotations

import os
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import Principal
from ..control_schemas import (
    AgentMessageCreate,
    AgentMessageOut,
    AgentStateOut,
    AgentStateUpdate,
    AgentTaskCreate,
    AgentTaskOut,
    AgentTaskUpdate,
    AgentToolPolicyCreate,
    AgentToolPolicyOut,
)
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import AgentMessage, AgentState, AgentTask, AgentToolPolicy
from ..permissions import has_permission
from ..time_utils import utcnow, iso_local
from agents.catalog import catalog_as_dicts

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
def list_resource() -> dict:
    return {
        "module": "agents",
        "description": "DB-backed agent task queue, message bus, state, and tool policies",
        "mode": "governed-monitor-only",
    }


@router.get("/catalog")
def catalog() -> dict:
    return {"agents": catalog_as_dicts()}


@router.get("/runtime-summary")
def runtime_summary(
    stale_after_seconds: int = Query(default=180, ge=30, le=3600),
    db: Session = Depends(get_db),
) -> dict:
    status_counts = {
        str(status): int(count)
        for status, count in db.execute(select(AgentTask.status, func.count()).group_by(AgentTask.status)).all()
    }
    total_tasks = int(sum(status_counts.values()))
    queued_tasks = int(status_counts.get("queued", 0))
    running_tasks = int(status_counts.get("running", 0))
    retrying_tasks = int(status_counts.get("retrying", 0))
    failed_tasks = int(status_counts.get("failed", 0))
    completed_tasks = int(status_counts.get("completed", 0))

    oldest_queued = db.scalar(select(func.min(AgentTask.created_at)).where(AgentTask.status == "queued"))
    oldest_queued_age_seconds = None
    if oldest_queued:
        oldest_queued_age_seconds = max(0, int((utcnow() - oldest_queued).total_seconds()))

    failed = db.scalar(select(AgentTask).where(AgentTask.status == "failed").order_by(AgentTask.updated_at.desc()).limit(1))
    last_failed_task = None
    if failed:
        detail = ""
        if isinstance(failed.result_json, dict):
            detail = str(failed.result_json.get("reason") or failed.result_json.get("error") or "").strip()
        last_failed_task = {
            "task_id": failed.task_id,
            "assigned_agent": failed.assigned_agent,
            "task_type": failed.task_type,
            "attempts": failed.attempts,
            "max_attempts": failed.max_attempts,
            "updated_at": iso_local(failed.updated_at),
            "detail": detail,
        }

    cutoff = utcnow().timestamp() - stale_after_seconds
    states = db.scalars(select(AgentState)).all()
    stale_states = []
    for row in states:
        heartbeat = row.heartbeat_at or row.updated_at
        if not heartbeat:
            continue
        if heartbeat.timestamp() < cutoff:
            stale_states.append(
                {
                    "agent_name": row.agent_name,
                    "status": row.status,
                    "last_heartbeat_at": iso_local(heartbeat),
                    "stale_for_seconds": int(utcnow().timestamp() - heartbeat.timestamp()),
                }
            )

    retry_pressure = queued_tasks > 0 and (failed_tasks > 0 or retrying_tasks > 0)
    orchestrator_health = "degraded" if stale_states or retry_pressure else "healthy"
    recovery_actions: list[str] = []
    if stale_states:
        recovery_actions.append("Run POST /api/v1/agents/recover-stale to reset stale agent states to standby.")
    if failed_tasks > 0:
        recovery_actions.append("Inspect last_failed_task and resubmit a bounded task with lower scope.")
    if queued_tasks > 10:
        recovery_actions.append("Queue depth is elevated; prioritize watchdog or orchestrator triage tasks.")
    retry_policy = {
        "default_max_attempts": 3,
        "workflow_poll_interval_seconds": int(os.getenv("AGENT_WORKFLOW_INTERVAL_SECONDS", "5")),
        "retry_states": ["retrying"],
        "manual_recovery_endpoint": "/api/v1/agents/recover-stale",
        "stale_threshold_seconds": stale_after_seconds,
    }
    return {
        "orchestrator_health": orchestrator_health,
        "total_tasks": total_tasks,
        "queued_tasks": queued_tasks,
        "running_tasks": running_tasks,
        "retrying_tasks": retrying_tasks,
        "failed_tasks": failed_tasks,
        "completed_tasks": completed_tasks,
        "oldest_queued_at": iso_local(oldest_queued) if oldest_queued else None,
        "oldest_queued_age_seconds": oldest_queued_age_seconds,
        "last_failed_task": last_failed_task,
        "stale_agents_count": len(stale_states),
        "stale_agents": stale_states[:20],
        "stale_threshold_seconds": stale_after_seconds,
        "status_counts": status_counts,
        "retry_policy": retry_policy,
        "recovery_actions": recovery_actions,
    }


@router.post("/recover-stale")
def recover_stale(
    stale_after_seconds: int = Query(default=180, ge=30, le=3600),
    queue_watchdog_review: bool = Query(default=True),
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> dict:
    if not has_permission(principal.role, "agents:write"):
        raise HTTPException(status_code=403, detail="Permission denied")

    now = utcnow()
    cutoff_ts = now.timestamp() - stale_after_seconds
    states = db.scalars(select(AgentState)).all()
    recovered: list[dict] = []
    for row in states:
        heartbeat = row.heartbeat_at or row.updated_at
        if not heartbeat or heartbeat.timestamp() >= cutoff_ts:
            continue
        previous_status = row.status
        row.status = "standby"
        state_json = dict(row.state_json or {})
        state_json.update(
            {
                "recovered_by": principal.user_id,
                "recovered_at": iso_local(now),
                "previous_status": previous_status,
                "stale_threshold_seconds": stale_after_seconds,
            }
        )
        row.state_json = state_json
        row.heartbeat_at = now
        row.updated_at = now
        recovered.append(
            {
                "agent_name": row.agent_name,
                "previous_status": previous_status,
                "last_heartbeat_at": iso_local(heartbeat),
            }
        )

    queued_watchdog_task = None
    if queue_watchdog_review and recovered:
        watchdog_task = AgentTask(
            task_id=_task_id(),
            requested_by=principal.user_id,
            assigned_agent="Watchdog Agent",
            task_type="stale_recovery_review",
            status="queued",
            priority=2,
            request_json={"recovered_agents": [item["agent_name"] for item in recovered], "count": len(recovered)},
            max_attempts=3,
        )
        db.add(watchdog_task)
        queued_watchdog_task = watchdog_task.task_id

    audit(
        db,
        principal,
        "recover_stale_agents",
        "agent_state",
        "stale_recovery",
        {"stale_after_seconds": stale_after_seconds, "recovered_count": len(recovered), "watchdog_task": queued_watchdog_task},
    )
    db.commit()
    return {
        "status": "completed",
        "recovered_count": len(recovered),
        "recovered_agents": recovered,
        "watchdog_task_id": queued_watchdog_task,
    }


def _task_id() -> str:
    return f"task_{secrets.token_hex(8)}"


def _message_id() -> str:
    return f"msg_{secrets.token_hex(8)}"


@router.get("/tasks", response_model=list[AgentTaskOut])
def list_tasks(status: str | None = None, db: Session = Depends(get_db)) -> list[AgentTask]:
    query = select(AgentTask).order_by(AgentTask.created_at.desc()).limit(200)
    if status:
        query = select(AgentTask).where(AgentTask.status == status).order_by(AgentTask.created_at.desc()).limit(200)
    return list(db.scalars(query))


@router.post("/tasks", response_model=AgentTaskOut)
def create_task(payload: AgentTaskCreate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> AgentTask:
    if not has_permission(principal.role, "agents:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    task = AgentTask(
        task_id=_task_id(),
        requested_by=principal.user_id,
        assigned_agent=payload.assigned_agent,
        task_type=payload.task_type,
        priority=payload.priority,
        request_json=payload.request_json,
        max_attempts=payload.max_attempts,
    )
    db.add(task)
    audit(db, principal, "create", "agent_task", task.task_id, {"assigned_agent": payload.assigned_agent, "task_type": payload.task_type})
    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}", response_model=AgentTaskOut)
def update_task(task_id: str, payload: AgentTaskUpdate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> AgentTask:
    if not has_permission(principal.role, "agents:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    task = db.scalar(select(AgentTask).where(AgentTask.task_id == task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = payload.status
    task.result_json = payload.result_json
    task.updated_at = utcnow()
    if payload.status in {"running", "retrying"}:
        task.attempts += 1
    audit(db, principal, "update", "agent_task", task_id, {"status": payload.status})
    db.commit()
    db.refresh(task)
    return task


@router.get("/messages", response_model=list[AgentMessageOut])
def list_messages(task_id: str | None = None, db: Session = Depends(get_db)) -> list[AgentMessage]:
    query = select(AgentMessage).order_by(AgentMessage.created_at.desc()).limit(200)
    if task_id:
        query = select(AgentMessage).where(AgentMessage.task_id == task_id).order_by(AgentMessage.created_at.desc()).limit(200)
    return list(db.scalars(query))


@router.post("/messages", response_model=AgentMessageOut)
def create_message(payload: AgentMessageCreate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> AgentMessage:
    if not has_permission(principal.role, "agents:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    message = AgentMessage(message_id=_message_id(), **payload.model_dump())
    db.add(message)
    audit(db, principal, "create", "agent_message", message.message_id, {"sender": payload.sender_agent, "recipient": payload.recipient_agent})
    db.commit()
    db.refresh(message)
    return message


@router.get("/states", response_model=list[AgentStateOut])
def list_states(db: Session = Depends(get_db)) -> list[AgentState]:
    return list(db.scalars(select(AgentState).order_by(AgentState.updated_at.desc()).limit(200)))


@router.post("/states/{agent_name}", response_model=AgentStateOut)
def update_state(agent_name: str, payload: AgentStateUpdate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> AgentState:
    if not has_permission(principal.role, "agents:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    state = db.scalar(select(AgentState).where(AgentState.agent_name == agent_name))
    if state:
        state.status = payload.status
        state.state_json = payload.state_json
        state.heartbeat_at = utcnow()
        state.updated_at = utcnow()
    else:
        state = AgentState(agent_name=agent_name, status=payload.status, state_json=payload.state_json, heartbeat_at=utcnow())
        db.add(state)
    audit(db, principal, "upsert", "agent_state", agent_name, {"status": payload.status})
    db.commit()
    db.refresh(state)
    return state


@router.get("/tool-policies", response_model=list[AgentToolPolicyOut])
def list_tool_policies(db: Session = Depends(get_db)) -> list[AgentToolPolicy]:
    return list(db.scalars(select(AgentToolPolicy).order_by(AgentToolPolicy.created_at.desc()).limit(200)))


@router.post("/tool-policies", response_model=AgentToolPolicyOut)
def create_tool_policy(payload: AgentToolPolicyCreate, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> AgentToolPolicy:
    if not has_permission(principal.role, "agents:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    policy = AgentToolPolicy(**payload.model_dump())
    db.add(policy)
    audit(db, principal, "create", "agent_tool_policy", f"{payload.agent_name}:{payload.tool_name}", {"allowed": payload.allowed})
    db.commit()
    db.refresh(policy)
    return policy
