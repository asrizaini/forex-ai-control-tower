from __future__ import annotations

import json
import os
import signal
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from control.api.time_utils import utcnow
from pathlib import Path

from sqlalchemy import select

from agent_theater.loki import push_event
from agents.catalog import AGENT_CATALOG
from control.api.db import SessionLocal, init_db
from control.api.models import AgentMessage, AgentState, AgentTask, AgentToolPolicy
from control.api.time_utils import format_local


running = True


@dataclass(frozen=True)
class WorkflowResult:
    summary: str
    risk_status: str
    next_action: str


def _stop(_signum: int, _frame: object) -> None:
    global running
    running = False


def _local_timestamp() -> str:
    return format_local(utcnow())


def _event_log_path() -> Path:
    return Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))


def _message_id() -> str:
    return f"msg_{int(time.time() * 1000)}"


def _workflow_response(task: AgentTask) -> WorkflowResult:
    agent = task.assigned_agent
    task_type = task.task_type
    if agent == "Risk Manager":
        return WorkflowResult(
            summary="Risk Manager reviewed the queued request in monitor-only mode. No approval, order, or risk-policy change was executed.",
            risk_status="review_complete_no_execution",
            next_action="Create or update a governed risk policy before enabling any demo approval flow.",
        )
    if agent == "Market Data Agent":
        return WorkflowResult(
            summary="Market Data Agent reviewed the queued request against MT5 telemetry. Stale or incomplete market data remains blocked from signal generation.",
            risk_status="data_quality_gate_active",
            next_action="Wait for fresh ticks and candle history before technical signal scoring.",
        )
    if agent == "Strategy Agent":
        return WorkflowResult(
            summary="Strategy Agent accepted the queued request for governance review. Strategy output remains non-executable until backtest, forward test, demo validation, and approval gates pass.",
            risk_status="strategy_governance_required",
            next_action="Attach a registered strategy_id and run validation before any signal proposal.",
        )
    if agent == "Deployment Agent":
        return WorkflowResult(
            summary="Deployment Agent recorded the queued request. Production changes require backup, changelog, smoke test result, approver, and rollback command.",
            risk_status="deployment_governance_required",
            next_action="Prepare a deployment record before applying changes to production-live workflows.",
        )
    return WorkflowResult(
        summary=f"{agent} processed queued task type {task_type} in safe workflow mode.",
        risk_status="workflow_complete_no_execution",
        next_action="Review the task result and queue a more specific agent task if needed.",
    )


def _append_theater_event(event: dict) -> None:
    event_log = _event_log_path()
    event_log.parent.mkdir(parents=True, exist_ok=True)
    with event_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    push_event(event)


def _upsert_state(db, agent_name: str, status: str, state: dict) -> None:
    now = utcnow()
    record = db.scalar(select(AgentState).where(AgentState.agent_name == agent_name))
    if record:
        record.status = status
        record.state_json = state
        record.heartbeat_at = now
        record.updated_at = now
    else:
        db.add(AgentState(agent_name=agent_name, status=status, state_json=state, heartbeat_at=now, updated_at=now))


def seed_agent_catalog() -> int:
    init_db()
    db = SessionLocal()
    try:
        now = utcnow()
        count = 0
        for entry in AGENT_CATALOG:
            record = db.scalar(select(AgentState).where(AgentState.agent_name == entry.name))
            state = {"role": entry.role, "tool_policy": entry.tool_policy, "notes": entry.notes}
            if record:
                if record.status in {"running"}:
                    continue
                record.status = entry.status
                record.state_json = {**(record.state_json or {}), **state}
                record.heartbeat_at = now
                record.updated_at = now
            else:
                db.add(AgentState(agent_name=entry.name, status=entry.status, state_json=state, heartbeat_at=now, updated_at=now))
            existing_policy = db.scalar(
                select(AgentToolPolicy)
                .where(AgentToolPolicy.agent_name == entry.name)
                .where(AgentToolPolicy.tool_name == entry.tool_policy)
            )
            if not existing_policy:
                db.add(
                    AgentToolPolicy(
                        agent_name=entry.name,
                        tool_name=entry.tool_policy,
                        allowed=entry.tool_policy not in {"restricted", "no_direct_mt5", "adapter_pending"},
                        environment="demo",
                        reason=entry.notes,
                    )
                )
            count += 1
        db.commit()
        return count
    finally:
        db.close()


def process_one_task() -> str | None:
    init_db()
    db = SessionLocal()
    try:
        task = db.scalar(
            select(AgentTask)
            .where(AgentTask.status == "queued")
            .order_by(AgentTask.priority.asc(), AgentTask.created_at.asc())
            .limit(1)
        )
        if not task:
            return None

        task.status = "running"
        task.attempts += 1
        task.updated_at = utcnow()
        _upsert_state(db, task.assigned_agent, "running", {"task_id": task.task_id, "task_type": task.task_type})
        db.add(
            AgentMessage(
                message_id=_message_id(),
                task_id=task.task_id,
                sender_agent="Orchestrator Agent",
                recipient_agent=task.assigned_agent,
                message_type="task_dispatch",
                payload_json={"task_type": task.task_type, "request": task.request_json},
            )
        )
        db.commit()

        result = _workflow_response(task)
        task.status = "completed"
        task.result_json = asdict(result)
        task.updated_at = utcnow()
        _upsert_state(db, task.assigned_agent, "standby", {"last_task_id": task.task_id, "last_result": result.risk_status})
        db.add(
            AgentMessage(
                message_id=_message_id(),
                task_id=task.task_id,
                sender_agent=task.assigned_agent,
                recipient_agent="Orchestrator Agent",
                message_type="task_result",
                payload_json=asdict(result),
            )
        )
        db.commit()
        _append_theater_event(
            {
                "timestamp": _local_timestamp(),
                "agent": task.assigned_agent,
                "stream": "Workflow Timeline",
                "summary": result.summary,
                "input_sources": ["agent_tasks", "workflow_engine"],
                "result": "task_completed",
                "confidence": 0.82,
                "risk_status": result.risk_status,
                "next_action": result.next_action,
                "metadata": {"task_id": task.task_id, "task_type": task.task_type},
                "contains_hidden_chain_of_thought": False,
            }
        )
        return task.task_id
    finally:
        db.close()


def main() -> int:
    interval_seconds = int(os.getenv("AGENT_WORKFLOW_INTERVAL_SECONDS", "5"))
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while running:
        try:
            seed_agent_catalog()
            processed = process_one_task()
            if processed:
                print(json.dumps({"event": "agent_task_processed", "task_id": processed}), flush=True)
        except Exception as exc:  # pragma: no cover - service safety boundary
            print(json.dumps({"event": "agent_workflow_error", "error": type(exc).__name__}), flush=True)
        time.sleep(interval_seconds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
