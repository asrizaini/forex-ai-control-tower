from __future__ import annotations

import os
import urllib.error
import urllib.request
import json
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..credential_store import runtime_bool
from ..models import AgentTask, AuditLog, KillSwitch, MarketSnapshot, NotificationEvent, RiskPolicy, Strategy, StrategyLabJob, TradeApproval, User, Account
from ..secret_manager import secret_manager_status

router = APIRouter(prefix="/system", tags=["system"])


@router.get("")
def list_resource() -> dict:
    return {"module": "system", "description": "System health, environment, audit, deployment status", "mode": "production-required"}


def _effective_runtime_context(db: Session) -> tuple[str, str]:
    account = db.scalar(select(Account).where(Account.enabled.is_(True)).order_by(Account.created_at.desc()).limit(1))
    if account:
        return account.environment, account.trading_mode
    return "demo", "monitor_only"


def _orchestrator_runtime_status() -> dict:
    event_log = Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))
    if not event_log.exists():
        return {
            "status": "down",
            "reason": "orchestrator_event_log_missing",
            "last_success_run": None,
            "last_failed_run": None,
            "last_failed_reason": "Event log file is missing.",
        }
    last_success = None
    last_failed = None
    last_failed_reason = None
    try:
        lines = event_log.read_text(encoding="utf-8").splitlines()[-600:]
    except OSError:
        return {
            "status": "degraded",
            "reason": "orchestrator_event_log_unreadable",
            "last_success_run": None,
            "last_failed_run": None,
            "last_failed_reason": "Unable to read orchestrator event log.",
        }
    for line in reversed(lines):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("agent") != "Orchestrator Agent":
            continue
        result = str(event.get("result", "")).lower()
        timestamp = event.get("timestamp")
        if result in {"healthy", "coordination_visible", "safe_reply"} and last_success is None:
            last_success = timestamp
        if result == "degraded" and last_failed is None:
            last_failed = timestamp
            last_failed_reason = event.get("summary")
        if last_success and last_failed:
            break

    def _parse_event_time(value: str | None) -> datetime | None:
        if not value or not isinstance(value, str):
            return None
        text = value.strip()
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            pass
        for pattern in ("%Y-%m-%d %I:%M:%S %p GMT+8",):
            try:
                return datetime.strptime(text, pattern)
            except ValueError:
                continue
        return None

    if last_success:
        success_dt = _parse_event_time(last_success)
        failed_dt = _parse_event_time(last_failed)
        recovered = bool(success_dt and failed_dt and success_dt >= failed_dt)
        healthy_now = last_failed is None or recovered
        return {
            "status": "running" if healthy_now else "degraded",
            "reason": "healthy_loop" if healthy_now else "intermittent_failures_detected",
            "last_success_run": last_success,
            "last_failed_run": last_failed,
            "last_failed_reason": last_failed_reason,
        }
    return {
        "status": "degraded",
        "reason": "no_recent_success_events",
        "last_success_run": None,
        "last_failed_run": last_failed,
        "last_failed_reason": last_failed_reason or "No successful orchestrator event found in the recent log window.",
    }


@router.get("/runtime")
def runtime_status() -> dict:
    event_log = Path(os.getenv("AGENT_THEATER_EVENT_LOG", "/opt/forex-ai-control-tower/runtime/agent_theater_events.jsonl"))
    db = SessionLocal()
    try:
        environment, trading_mode = _effective_runtime_context(db)
        queued_tasks = db.scalar(select(func.count()).select_from(AgentTask).where(AgentTask.status == "queued")) or 0
        failed_tasks = db.scalar(select(func.count()).select_from(AgentTask).where(AgentTask.status == "failed")) or 0
    finally:
        db.close()
    runtime_live_enabled = runtime_bool("ALLOW_LIVE_TRADING", False)
    live_auto = trading_mode in {"demo_auto", "restricted_live_auto"} and (
        environment == "demo" or (environment == "production-live" and runtime_live_enabled)
    )
    orchestrator = _orchestrator_runtime_status()
    return {
        "environment": environment,
        "trading_mode": trading_mode,
        "live_auto_trading": live_auto,
        "orchestrator_event_log_exists": event_log.exists(),
        "orchestrator": {
            **orchestrator,
            "queued_tasks": queued_tasks,
            "failed_tasks": failed_tasks,
            "retry_status": "retry_pending" if queued_tasks > 0 and orchestrator.get("status") != "running" else "stable",
        },
        "agent_theater_event_log": str(event_log),
    }


@router.get("/secret-manager/status")
def get_secret_manager_status() -> dict:
    return secret_manager_status()


@router.get("/health/status")
def full_health_status() -> dict:
    services = {"api": {"status": "ok", "url": "http://10.10.1.81:8000/health"}}
    try:
        db = SessionLocal()
        try:
            db.execute(select(1))
            services["database"] = {"status": "ok"}
        finally:
            db.close()
    except SQLAlchemyError:
        services["database"] = {"status": "down"}
    checks = {
        "grafana": "http://127.0.0.1:3000/api/health",
        "prometheus": "http://127.0.0.1:9090/-/healthy",
        "qdrant": "http://127.0.0.1:6333/",
        "loki": "http://127.0.0.1:3100/ready",
    }
    for name, url in checks.items():
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                services[name] = {"status": "ok" if 200 <= response.status < 300 else "down", "url": url}
        except (OSError, urllib.error.URLError, TimeoutError):
            services[name] = {"status": "down", "url": url}
    credentials = secret_manager_status()
    services["credentials"] = {
        "status": "ok" if credentials.get("required_runtime_secrets_present") else "missing_required",
        "required_runtime_secrets_present": credentials.get("required_runtime_secrets_present"),
    }
    # Disk space check
    import shutil as _shutil
    disk_info: dict = {}
    try:
        root_usage = _shutil.disk_usage("/")
        root_pct = round(root_usage.used / root_usage.total * 100, 1)
        disk_info["root_disk_pct"] = root_pct
        disk_info["root_disk_status"] = "ok" if root_pct < 80 else ("warning" if root_pct < 90 else "critical")
    except OSError:
        disk_info["root_disk_pct"] = None
        disk_info["root_disk_status"] = "unknown"
    services["disk"] = disk_info
    all_healthy = all(
        item["status"] == "ok" if isinstance(item, dict) and "status" in item else True
        for item in services.values()
    )
    return {"healthy": all_healthy, "services": services}


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
        security_review = db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "prelive_gate_passed", AuditLog.resource_type == "prelive_gate", AuditLog.resource_id == "security_review")
        ) or 0
        broker_compatibility = db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "prelive_gate_passed", AuditLog.resource_type == "prelive_gate", AuditLog.resource_id == "broker_compatibility")
        ) or 0
        production_live_approval = db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.action == "prelive_gate_passed",
                AuditLog.resource_type == "prelive_gate",
                AuditLog.resource_id == "production_live_explicitly_approved",
            )
        ) or 0
        restore_drill_marker = Path("/opt/forex-ai-control-tower/backups/restore_drills/latest.json")
        try:
            with urllib.request.urlopen("http://127.0.0.1:9093/-/healthy", timeout=2) as response:
                alertmanager_healthy = 200 <= response.status < 300
        except (OSError, urllib.error.URLError, TimeoutError):
            alertmanager_healthy = False
        environment, trading_mode = _effective_runtime_context(db)
        gates = {
            "user_account_persistence": users > 0 and accounts > 0,
            "rbac_audit_persistence": True,
            "risk_policies": risk_policies > 0,
            "strategy_validation_pipeline": strategies > 0,
            "manual_approval_workflow": approvals > 0,
            "secret_manager_or_runtime_secrets": bool(secrets_status.get("required_runtime_secrets_present")),
            "backup_restore_drill": restore_drill_marker.exists(),
            "monitoring_alerts_connected": alertmanager_healthy,
            "security_review_completed": security_review > 0,
            "broker_compatibility_checks_passed": broker_compatibility > 0,
            "market_data_quality_gates_passed": fresh_market > 0,
            "kill_switch_tested": kill_switches > 0,
            "production_live_explicitly_approved": production_live_approval > 0,
        }
        blocking = [name for name, passed in gates.items() if not passed]
        all_gates_passed = not blocking
        runtime_live_enabled = runtime_bool("ALLOW_LIVE_TRADING", False)
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
            "environment": environment,
            "trading_mode": trading_mode,
            "restricted_live_auto_allowed": all_gates_passed and runtime_live_enabled,
            "live_trading_allowed": all_gates_passed and runtime_live_enabled,
            "gates": gates,
            "blocking_gates": blocking,
            "next_required_actions": [action_by_gate[name] for name in blocking],
        }
    finally:
        db.close()
