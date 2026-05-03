from __future__ import annotations

import os
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import func, select

from ..db import SessionLocal
from ..models import AgentTask, KillSwitch, MarketSnapshot, NotificationEvent, RiskPolicy, Strategy, StrategyLabJob, TradeApproval, User, Account
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


@router.get("/production-readiness")
def production_readiness() -> dict:
    db = SessionLocal()
    try:
        secrets_status = secret_manager_status()
        users = db.scalar(select(func.count()).select_from(User)) or 0
        accounts = db.scalar(select(func.count()).select_from(Account)) or 0
        risk_policies = db.scalar(select(func.count()).select_from(RiskPolicy)) or 0
        strategies = db.scalar(select(func.count()).select_from(Strategy)) or 0
        approvals = db.scalar(select(func.count()).select_from(TradeApproval)) or 0
        kill_switches = db.scalar(select(func.count()).select_from(KillSwitch)) or 0
        fresh_market = db.scalar(select(func.count()).select_from(MarketSnapshot).where(MarketSnapshot.feed_fresh.is_(True))) or 0
        restore_drill_marker = Path("/opt/forex-ai-control-tower/backups/restore_drills/latest.json")
        try:
            with urllib.request.urlopen("http://127.0.0.1:9093/-/healthy", timeout=2) as response:
                alertmanager_healthy = 200 <= response.status < 300
        except (OSError, urllib.error.URLError, TimeoutError):
            alertmanager_healthy = False
        gates = {
            "user_account_persistence": users > 0 and accounts > 0,
            "rbac_audit_persistence": True,
            "risk_policies": risk_policies > 0,
            "strategy_validation_pipeline": strategies > 0,
            "manual_approval_workflow": approvals > 0,
            "secret_manager_or_runtime_secrets": bool(secrets_status.get("required_runtime_secrets_present")),
            "backup_restore_drill": restore_drill_marker.exists(),
            "monitoring_alerts_connected": alertmanager_healthy,
            "security_review_completed": False,
            "broker_compatibility_checks_passed": False,
            "market_data_quality_gates_passed": fresh_market > 0,
            "kill_switch_tested": kill_switches > 0,
            "production_live_explicitly_approved": False,
        }
        blocking = [name for name, passed in gates.items() if not passed]
        action_by_gate = {
            "user_account_persistence": "Create at least one admin/user account and one MT5 account record.",
            "rbac_audit_persistence": "Verify RBAC and append-only audit persistence.",
            "risk_policies": "Create default demo and account risk policies.",
            "strategy_validation_pipeline": "Register at least one strategy and run backtest, forward-test, tuning, and demo validation records.",
            "manual_approval_workflow": "Run a demo manual approval request and decision through the dashboard or API.",
            "secret_manager_or_runtime_secrets": "Set required runtime secrets through environment or the approved secret manager.",
            "backup_restore_drill": "Complete a backup restore drill and write the restore drill marker.",
            "monitoring_alerts_connected": "Start Alertmanager and connect monitoring alerts to the notification hub.",
            "security_review_completed": "Complete the pre-live security review checklist.",
            "broker_compatibility_checks_passed": "Run broker compatibility checks against the logged-in MT5 demo terminal.",
            "market_data_quality_gates_passed": "Collect fresh MT5 market data and pass market data quality gates.",
            "kill_switch_tested": "Execute and audit a demo kill-switch test.",
            "production_live_explicitly_approved": "Explicitly approve production-live only after demo validation reports pass.",
        }
        return {
            "environment": "demo",
            "trading_mode": "monitor_only",
            "restricted_live_auto_allowed": False,
            "live_trading_allowed": False,
            "gates": gates,
            "blocking_gates": blocking,
            "next_required_actions": [action_by_gate[name] for name in blocking],
        }
    finally:
        db.close()
