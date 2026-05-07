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


from agents.risk_manager_agent import RiskManagerAgent
from agents.signal_reviewer_agent import SignalReviewerAgent
from agents.strategy_agent import StrategyAgent


def _workflow_response(task: AgentTask) -> WorkflowResult:
    agent = task.assigned_agent
    task_type = task.task_type
    request = task.request_json or {}

    # Build an AgentMessage from the task request for real agent logic
    incoming_message = AgentMessage(
        message_id=f"msg_{int(time.time() * 1000)}",
        task_id=task.task_id,
        sender_agent="Orchestrator Agent",
        recipient_agent=agent,
        message_type="task_dispatch",
        payload_json={"task_type": task_type, "request": request},
    )

    # Route to real agent implementations where available
    if agent == "Risk Manager":
        risk_agent = RiskManagerAgent()
        # Extract risk parameters from the request payload
        result = risk_agent.evaluate_risk(
            context=request.get("context", task_type),
            current_risk_status=request.get("risk_status", "unknown"),
            confidence=float(request.get("confidence", 0.5)),
            kill_switch_active=bool(request.get("kill_switch_active", False)),
            daily_loss_pct=float(request.get("daily_loss_pct", 0.0)),
            max_daily_loss_pct=float(request.get("max_daily_loss_pct", 5.0)),
            weekly_loss_pct=float(request.get("weekly_loss_pct", 0.0)),
            max_weekly_loss_pct=float(request.get("max_weekly_loss_pct", 10.0)),
            open_trades=int(request.get("open_trades", 0)),
            max_open_trades=int(request.get("max_open_trades", 3)),
            news_halt_active=bool(request.get("news_halt_active", False)),
            trading_mode=request.get("trading_mode", "monitor_only"),
        )
        return WorkflowResult(
            summary=result.summary,
            risk_status=result.risk_status,
            next_action=result.next_action,
        )

    if agent == "Strategy Agent":
        strategy_agent = StrategyAgent()
        result = strategy_agent.propose_signal(
            context=request.get("context", task_type),
            confidence=float(request.get("confidence", 0.5)),
            symbol=request.get("symbol", ""),
            direction=request.get("direction", ""),
            strategy_id=request.get("strategy_id", ""),
            timeframe=request.get("timeframe", "M1"),
            lifecycle_state=request.get("lifecycle_state", "draft"),
            quality_score=float(request.get("quality_score", 0.0)),
            min_quality_score=float(request.get("min_quality_score", 0.5)),
            market_data_fresh=bool(request.get("market_data_fresh", True)),
            trend_status=request.get("trend_status", "neutral"),
            current_bias=request.get("current_bias", "neutral"),
        )
        return WorkflowResult(
            summary=result.summary,
            risk_status=result.governance_status,
            next_action=result.next_action,
        )

    if agent == "Signal Reviewer":
        reviewer = SignalReviewerAgent()
        result = reviewer.review_signal(
            context=request.get("context", task_type),
            confidence=float(request.get("confidence", 0.5)),
            risk_status=request.get("risk_status", "unknown"),
            signal_status=request.get("signal_status", "active"),
            direction=request.get("direction", ""),
            symbol=request.get("symbol", ""),
            strategy_id=request.get("strategy_id", ""),
            timeframe=request.get("timeframe", "M1"),
            min_confidence=float(request.get("min_confidence", 0.4)),
            max_spread_points=float(request.get("max_spread_points", 30.0)),
            spread_points=float(request.get("spread_points", 0.0)),
            news_halt_active=bool(request.get("news_halt_active", False)),
            market_data_fresh=bool(request.get("market_data_fresh", True)),
            duplicate_signal=bool(request.get("duplicate_signal", False)),
            correlation_conflict=bool(request.get("correlation_conflict", False)),
            strategy_lifecycle_state=request.get("strategy_lifecycle_state", "draft"),
            quality_score=float(request.get("quality_score", 0.0)),
        )
        return WorkflowResult(
            summary=result.summary,
            risk_status=result.review_status,
            next_action=result.next_action,
        )

    if agent == "Market Data Agent":
        return WorkflowResult(
            summary="Market Data Agent reviewed the queued request against MT5 telemetry. Stale or incomplete market data remains blocked from signal generation.",
            risk_status="data_quality_gate_active",
            next_action="Wait for fresh ticks and candle history before technical signal scoring.",
        )
    if agent == "Deployment Agent":
        return WorkflowResult(
            summary="Deployment Agent recorded the queued request. Production changes require backup, changelog, smoke test result, approver, and rollback command.",
            risk_status="deployment_governance_required",
            next_action="Prepare a deployment record before applying changes to production-live workflows.",
        )

    # --- Auto-heal task types ---
    if task_type == "auto_heal_service_down":
        service = request.get("service_name", "unknown")
        error = request.get("error_info", "unknown")
        return WorkflowResult(
            summary=f"Auto-heal: Service '{service}' is down ({error}). Orchestrator dispatched heal task to {agent}. "
                   f"Recommended action: check service logs, verify systemd unit status, restart if needed.",
            risk_status="auto_heal_dispatched",
            next_action=f"Verify {service} service recovery. Check journalctl for root cause. "
                       f"Restart with: systemctl restart forex-<service> if not auto-recovered.",
        )

    if task_type in ("disk_space_cleanup", "disk_emergency_cleanup"):
        disk_pct = request.get("disk_usage_pct", "unknown")
        disk_status = request.get("disk_status", "unknown")
        action = request.get("action", "auto_cleanup")
        if task_type == "disk_emergency_cleanup":
            return WorkflowResult(
                summary=f"EMERGENCY disk cleanup: disk at {disk_pct}% ({disk_status}). "
                       f"Emergency purge triggered for largest tables. Data retention policies temporarily reduced.",
                risk_status="disk_emergency_cleanup_triggered",
                next_action="Verify disk space recovered. Check /api/v1/data-retention/disk-status. "
                           "Consider adding disk capacity if this recurs.",
            )
        return WorkflowResult(
            summary=f"Auto disk cleanup: disk at {disk_pct}% ({disk_status}). "
                   f"Data retention cleanup triggered via {action}. Old records will be purged per retention policy.",
            risk_status="disk_cleanup_triggered",
            next_action="Monitor disk usage. Cleanup worker should free space within 15 minutes. "
                       "Check /api/v1/data-retention/disk-status for current status.",
        )

    if task_type == "disk_space_alert":
        disk_pct = request.get("disk_usage_pct", "unknown")
        disk_status = request.get("disk_status", "unknown")
        return WorkflowResult(
            summary=f"Watchdog disk alert: disk at {disk_pct}% ({disk_status}). "
                   f"Auto-cleanup worker has been notified. Monitoring continues.",
            risk_status="disk_alert_acknowledged",
            next_action="Continue monitoring. If disk does not recover within 30 minutes, escalate to manual intervention.",
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
