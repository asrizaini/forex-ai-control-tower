from __future__ import annotations

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
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

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
def list_resource() -> dict:
    return {
        "module": "agents",
        "description": "DB-backed agent task queue, message bus, state, and tool policies",
        "mode": "governed-monitor-only",
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
    task.updated_at = datetime.utcnow()
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
        state.heartbeat_at = datetime.utcnow()
        state.updated_at = datetime.utcnow()
    else:
        state = AgentState(agent_name=agent_name, status=payload.status, state_json=payload.state_json, heartbeat_at=datetime.utcnow())
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

