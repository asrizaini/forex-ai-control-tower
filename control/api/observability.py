from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timedelta

from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .db import SessionLocal
from .models import (
    Account,
    AccountSnapshot,
    AgentTask,
    KillSwitch,
    MarketSnapshot,
    NotificationEvent,
    ReleaseRecord,
    RiskPolicy,
    Strategy,
    StrategyLabJob,
    User,
)

LOGGER = logging.getLogger("forex_ai_control_tower.api")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
LOGGER.handlers = [handler]
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False

API_REQUESTS_TOTAL = Counter(
    "forex_api_requests_total",
    "Control API HTTP requests by method, path, and status.",
    ["method", "path", "status"],
)
API_REQUEST_LATENCY_SECONDS = Histogram(
    "forex_api_request_latency_seconds",
    "Control API HTTP request latency by method and path.",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
CONTROL_PLANE_RECORDS = Gauge(
    "forex_control_plane_records",
    "Control-plane database records by entity.",
    ["entity"],
)
AGENT_TASKS = Gauge(
    "forex_agent_tasks",
    "Agent task queue count by assigned agent and status.",
    ["agent", "status"],
)
STRATEGY_LAB_JOBS = Gauge(
    "forex_strategy_lab_jobs",
    "Strategy Lab job count by type and status.",
    ["job_type", "status"],
)
NOTIFICATION_EVENTS = Gauge(
    "forex_notification_events",
    "Notification events by level and status.",
    ["level", "status"],
)
ACTIVE_KILL_SWITCHES = Gauge(
    "forex_active_kill_switches",
    "Active kill-switch count by scope.",
    ["scope"],
)
MARKET_DATA_SNAPSHOTS = Gauge(
    "forex_market_data_snapshots",
    "Market data snapshots by symbol and quality.",
    ["symbol", "quality"],
)
MARKET_DATA_STALE_SYMBOLS = Gauge(
    "forex_market_data_stale_symbols",
    "Count of recently observed symbols whose latest snapshot is stale or limited.",
)
RISK_POLICIES = Gauge(
    "forex_risk_policies",
    "Risk policy count by scope.",
    ["scope"],
)


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    return str(path)


class JsonAccessLogAndMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        started = time.perf_counter()
        path = _route_path(request)
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - started
            API_REQUESTS_TOTAL.labels(request.method, path, str(status_code)).inc()
            API_REQUEST_LATENCY_SECONDS.labels(request.method, path).observe(elapsed)
            LOGGER.info(
                json.dumps(
                    {
                        "event": "api_request",
                        "method": request.method,
                        "path": path,
                        "status": status_code,
                        "latency_ms": round(elapsed * 1000, 2),
                        "client": request.client.host if request.client else "unknown",
                    },
                    separators=(",", ":"),
                )
            )


def collect_database_metrics() -> None:
    db: Session = SessionLocal()
    try:
        CONTROL_PLANE_RECORDS.labels("users").set(db.scalar(select(func.count()).select_from(User)) or 0)
        CONTROL_PLANE_RECORDS.labels("accounts").set(db.scalar(select(func.count()).select_from(Account)) or 0)
        CONTROL_PLANE_RECORDS.labels("strategies").set(db.scalar(select(func.count()).select_from(Strategy)) or 0)
        CONTROL_PLANE_RECORDS.labels("risk_policies").set(db.scalar(select(func.count()).select_from(RiskPolicy)) or 0)
        CONTROL_PLANE_RECORDS.labels("market_snapshots").set(db.scalar(select(func.count()).select_from(MarketSnapshot)) or 0)
        CONTROL_PLANE_RECORDS.labels("account_snapshots").set(db.scalar(select(func.count()).select_from(AccountSnapshot)) or 0)
        CONTROL_PLANE_RECORDS.labels("release_records").set(db.scalar(select(func.count()).select_from(ReleaseRecord)) or 0)

        for agent, status, count in db.execute(
            select(AgentTask.assigned_agent, AgentTask.status, func.count()).group_by(AgentTask.assigned_agent, AgentTask.status)
        ):
            AGENT_TASKS.labels(agent or "unknown", status or "unknown").set(count)

        for job_type, status, count in db.execute(
            select(StrategyLabJob.job_type, StrategyLabJob.status, func.count()).group_by(StrategyLabJob.job_type, StrategyLabJob.status)
        ):
            STRATEGY_LAB_JOBS.labels(job_type or "unknown", status or "unknown").set(count)

        for level, status, count in db.execute(
            select(NotificationEvent.level, NotificationEvent.status, func.count()).group_by(NotificationEvent.level, NotificationEvent.status)
        ):
            NOTIFICATION_EVENTS.labels(level or "unknown", status or "unknown").set(count)

        for scope, count in db.execute(select(KillSwitch.scope, func.count()).where(KillSwitch.active.is_(True)).group_by(KillSwitch.scope)):
            ACTIVE_KILL_SWITCHES.labels(scope or "unknown").set(count)

        for scope, count in db.execute(select(RiskPolicy.scope, func.count()).group_by(RiskPolicy.scope)):
            RISK_POLICIES.labels(scope or "unknown").set(count)

        cutoff = datetime.utcnow() - timedelta(minutes=20)
        stale_symbols = 0
        latest_symbols = list(db.scalars(select(MarketSnapshot.symbol).group_by(MarketSnapshot.symbol)))
        for symbol in latest_symbols:
            latest = db.scalar(
                select(MarketSnapshot).where(MarketSnapshot.symbol == symbol).order_by(MarketSnapshot.created_at.desc()).limit(1)
            )
            if not latest:
                continue
            quality = latest.data_quality or "unknown"
            MARKET_DATA_SNAPSHOTS.labels(symbol, quality).set(
                db.scalar(select(func.count()).select_from(MarketSnapshot).where(MarketSnapshot.symbol == symbol, MarketSnapshot.data_quality == quality)) or 0
            )
            if quality != "ok" or not latest.feed_fresh or latest.created_at < cutoff:
                stale_symbols += 1
        MARKET_DATA_STALE_SYMBOLS.set(stale_symbols)
    finally:
        db.close()
