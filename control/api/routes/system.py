from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import func, select

from ..db import SessionLocal
from ..models import AgentTask, KillSwitch, MarketSnapshot, NotificationEvent, StrategyLabJob
from ..secret_manager import secret_manager_status

router = APIRouter(prefix="/system", tags=["system"])


@router.get("")
def list_resource() -> dict:
    return {"module": "system", "description": "System health, environment, audit, deployment status", "mode": "production-required"}


@router.get("/runtime")
def runtime_status() -> dict:
    event_log = Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))
    return {
        "environment": "demo",
        "trading_mode": "monitor_only",
        "live_auto_trading": False,
        "orchestrator_event_log_exists": event_log.exists(),
        "agent_theater_event_log": str(event_log),
    }


@router.get("/secret-manager/status")
def get_secret_manager_status() -> dict:
    return secret_manager_status()


@router.get("/observability")
def observability_status() -> dict:
    db = SessionLocal()
    try:
        agent_tasks = [
            {"agent": agent, "status": status, "count": count}
            for agent, status, count in db.execute(
                select(AgentTask.assigned_agent, AgentTask.status, func.count()).group_by(AgentTask.assigned_agent, AgentTask.status)
            )
        ]
        strategy_lab_jobs = [
            {"job_type": job_type, "status": status, "count": count}
            for job_type, status, count in db.execute(
                select(StrategyLabJob.job_type, StrategyLabJob.status, func.count()).group_by(StrategyLabJob.job_type, StrategyLabJob.status)
            )
        ]
        notifications = [
            {"level": level, "status": status, "count": count}
            for level, status, count in db.execute(
                select(NotificationEvent.level, NotificationEvent.status, func.count()).group_by(NotificationEvent.level, NotificationEvent.status)
            )
        ]
        active_kill_switches = [
            {"scope": scope, "count": count}
            for scope, count in db.execute(select(KillSwitch.scope, func.count()).where(KillSwitch.active.is_(True)).group_by(KillSwitch.scope))
        ]
        latest_market = [
            {"symbol": symbol, "quality": quality, "feed_fresh": feed_fresh, "created_at": created_at.isoformat()}
            for symbol, quality, feed_fresh, created_at in db.execute(
                select(MarketSnapshot.symbol, MarketSnapshot.data_quality, MarketSnapshot.feed_fresh, func.max(MarketSnapshot.created_at))
                .group_by(MarketSnapshot.symbol, MarketSnapshot.data_quality, MarketSnapshot.feed_fresh)
                .order_by(func.max(MarketSnapshot.created_at).desc())
                .limit(20)
            )
        ]
        return {
            "metrics_endpoint": "/metrics",
            "structured_api_access_logs": True,
            "prometheus_custom_metrics": [
                "forex_api_requests_total",
                "forex_api_request_latency_seconds",
                "forex_agent_tasks",
                "forex_strategy_lab_jobs",
                "forex_notification_events",
                "forex_active_kill_switches",
                "forex_market_data_stale_symbols",
            ],
            "agent_tasks": agent_tasks,
            "strategy_lab_jobs": strategy_lab_jobs,
            "notifications": notifications,
            "active_kill_switches": active_kill_switches,
            "latest_market": latest_market,
        }
    finally:
        db.close()
