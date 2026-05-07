from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import current_principal
from ..models import (
    AlertDeliveryHistory,
    AlertRule,
    AnalysisSnapshot,
    AuditLog,
    CalendarEvent,
    DataSourceConfig,
    NewsItem,
    SystemSetting,
    TradingPair,
    TradeExecution,
    SignalRecord,
    WorkerRun,
    WorkerStatus,
)
from news_feed.providers import PROVIDERS
from news_feed.adapter import evaluate_news_status
from notifications.hub import channel_status

from ..time_utils import utcnow, iso_local

router = APIRouter(tags=["control-center"])


DEFAULT_DATA_SOURCES = [
    {
        "source_id": "forex_factory_calendar",
        "name": "Forex Factory Calendar",
        "source_type": "calendar",
        "provider": "forex_factory",
        "enabled": False,
        "priority": 10,
        "config_json": {"storage_pattern": "last_run_monthly_history", "rate_limit_seconds": 30},
    },
    {
        "source_id": "market_calendar_tool",
        "name": "Market Calendar Tool",
        "source_type": "calendar",
        "provider": "market_calendar_tool",
        "enabled": False,
        "priority": 20,
        "config_json": {"sites": ["ForexFactory", "MetalsMine", "EnergyExch", "CryptoCraft"], "max_parallel_tasks": 3},
    },
    {
        "source_id": "forex_factory_scrapper_api",
        "name": "ForexFactoryScrapper API",
        "source_type": "calendar",
        "provider": "forex_factory_scrapper_api",
        "enabled": False,
        "priority": 30,
        "config_json": {"base_url": "", "pagination": {"limit": 100, "offset": 0}},
    },
    {
        "source_id": "fmp_economic_calendar",
        "name": "Financial Modeling Prep Economic Calendar",
        "source_type": "calendar",
        "provider": "fmp",
        "enabled": False,
        "priority": 40,
        "config_json": {"credential_name": "NEWS_PROVIDER_API_KEY"},
    },
]

DEFAULT_WORKERS = [
    ("calendar_worker", "Calendar Worker", "calendar", "degraded"),
    ("news_worker", "News Worker", "news", "degraded"),
    ("technical_analysis_worker", "Technical Analysis Worker", "technical_analysis", "standby"),
    ("fundamental_analysis_worker", "Fundamental Analysis Worker", "fundamental_analysis", "standby"),
    ("signal_generation_worker", "Signal Generation Worker", "signal", "standby"),
    ("risk_analysis_worker", "Risk Analysis Worker", "risk", "standby"),
    ("notification_worker", "Notification Worker", "notification", "standby"),
    ("data_validation_worker", "Data Validation Worker", "validation", "standby"),
]

DEFAULT_SETTINGS = {
    "global_timezone": ("Asia/Kuala_Lumpur", "string", "regional"),
    "default_currencies": ("USD,EUR,GBP,JPY,AUD,CAD,CHF,NZD,XAU", "csv", "market"),
    "default_impact_levels": ("high,medium", "csv", "market"),
    "default_scrape_interval_minutes": ("60", "integer", "scheduler"),
    "default_alert_interval_minutes": ("1", "integer", "scheduler"),
    "dashboard_refresh_interval_seconds": ("30", "integer", "dashboard"),
    "scraped_data_retention_days": ("365", "integer", "retention"),
    "signal_records_retention_days": ("30", "integer", "retention"),
    "historical_candles_retention_days": ("90", "integer", "retention"),
    "market_snapshots_retention_days": ("14", "integer", "retention"),
    "disk_warning_pct": ("80", "integer", "monitoring"),
    "disk_critical_pct": ("90", "integer", "monitoring"),
    "disk_emergency_pct": ("95", "integer", "monitoring"),
    "api_base_url": ("http://10.10.1.81:8000", "url", "integration"),
    "grafana_url": ("http://10.10.1.81:3000", "url", "integration"),
    "worker_concurrency": ("3", "integer", "workers"),
}


class DataSourcePayload(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    source_type: str = Field(pattern="^(calendar|news|market_data)$")
    provider: str = Field(min_length=1, max_length=120)
    enabled: bool = False
    priority: int = Field(default=100, ge=1, le=1000)
    refresh_interval_minutes: int = Field(default=60, ge=1, le=10080)
    timeout_seconds: int = Field(default=15, ge=3, le=120)
    retry_count: int = Field(default=2, ge=0, le=10)
    backoff_seconds: int = Field(default=30, ge=1, le=3600)
    allowed_currencies: list[str] = Field(default_factory=list)
    allowed_impacts: list[str] = Field(default_factory=list)
    date_range_mode: str = Field(default="weekly", max_length=40)
    timezone: str = Field(default="Asia/Kuala_Lumpur", max_length=80)
    config_json: dict[str, Any] = Field(default_factory=dict)


class AlertRulePayload(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    enabled: bool = True
    currencies: list[str] = Field(default_factory=list)
    impacts: list[str] = Field(default_factory=list)
    event_keywords: list[str] = Field(default_factory=list)
    exact_event_names: list[str] = Field(default_factory=list)
    weekdays: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    trading_pairs: list[str] = Field(default_factory=list)
    minutes_before: int = Field(default=45, ge=0, le=1440)
    delivery_targets: list[str] = Field(default_factory=lambda: ["dashboard"])
    severity: str = Field(default="warning", max_length=40)


class SettingPayload(BaseModel):
    setting_value: str = Field(max_length=2000)
    value_type: str = Field(default="string", max_length=40)
    category: str = Field(default="general", max_length=80)


def _now() -> datetime:
    return utcnow()


def _audit(db: Session, actor: str, action: str, resource_type: str, resource_id: str, details: dict[str, Any] | None = None) -> None:
    db.add(
        AuditLog(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            note="No secret values logged.",
        )
    )


def _require_admin(principal=Depends(current_principal)):
    if principal.role != "super_admin":
        raise HTTPException(status_code=403, detail="super_admin required")
    return principal


def _event_uid(source_id: str, currency: str, event_name: str, event_time: datetime) -> str:
    raw = f"{source_id}|{currency.upper()}|{event_name.strip().lower()}|{event_time.isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _serialize_dt(value: datetime | None) -> str | None:
    return iso_local(value) if value else None


def _source_dict(row: DataSourceConfig) -> dict[str, Any]:
    return {
        "source_id": row.source_id,
        "name": row.name,
        "source_type": row.source_type,
        "provider": row.provider,
        "enabled": row.enabled,
        "priority": row.priority,
        "refresh_interval_minutes": row.refresh_interval_minutes,
        "timeout_seconds": row.timeout_seconds,
        "retry_count": row.retry_count,
        "backoff_seconds": row.backoff_seconds,
        "allowed_currencies": row.allowed_currencies,
        "allowed_impacts": row.allowed_impacts,
        "date_range_mode": row.date_range_mode,
        "timezone": row.timezone,
        "config_json": row.config_json,
        "last_status": row.last_status,
        "last_error": row.last_error,
        "last_success_at": _serialize_dt(row.last_success_at),
        "last_failure_at": _serialize_dt(row.last_failure_at),
        "updated_at": _serialize_dt(row.updated_at),
    }


def _seed_control_center(db: Session) -> None:
    for item in DEFAULT_DATA_SOURCES:
        existing = db.scalar(select(DataSourceConfig).where(DataSourceConfig.source_id == item["source_id"]))
        if not existing:
            db.add(DataSourceConfig(**item))
    for worker_id, name, worker_type, status in DEFAULT_WORKERS:
        existing = db.scalar(select(WorkerStatus).where(WorkerStatus.worker_id == worker_id))
        if not existing:
            db.add(
                WorkerStatus(
                    worker_id=worker_id,
                    name=name,
                    worker_type=worker_type,
                    status=status,
                    next_run_at=_now() + timedelta(minutes=5),
                    health_json={"note": "Worker is registered; connect runtime scheduler for active execution."},
                )
            )
    for key, (value, value_type, category) in DEFAULT_SETTINGS.items():
        existing = db.scalar(select(SystemSetting).where(SystemSetting.setting_key == key))
        if not existing:
            db.add(SystemSetting(setting_key=key, setting_value=value, value_type=value_type, category=category))
    db.commit()


def _refresh_worker_runtime_status(db: Session) -> None:
    now = _now()
    try:
        news = evaluate_news_status(None)
    except Exception as exc:
        news = {"provider_enabled": False, "provider_error": type(exc).__name__, "events_count": 0, "risk_status": "news_safe_mode"}

    news_ready = bool(news.get("provider_enabled")) and not news.get("provider_error") and int(news.get("events_count") or 0) > 0
    enabled_pairs = db.scalar(select(func.count()).select_from(TradingPair).where(TradingPair.enabled.is_(True))) or 0
    latest_signals = db.scalar(select(func.count()).select_from(SignalRecord)) or 0
    sent_executions = db.scalar(select(func.count()).select_from(TradeExecution).where(TradeExecution.status == "sent")) or 0
    blocked_executions = db.scalar(select(func.count()).select_from(TradeExecution).where(TradeExecution.status == "blocked")) or 0
    failed_executions = db.scalar(select(func.count()).select_from(TradeExecution).where(TradeExecution.status == "failed")) or 0
    stale_pairs = db.scalar(select(func.count()).select_from(TradingPair).where(TradingPair.enabled.is_(True), TradingPair.status.ilike("%stale%"))) or 0
    notify_channels = channel_status()
    telegram_ready = bool(notify_channels.get("telegram", {}).get("delivery_enabled"))
    push_ready = bool(notify_channels.get("mobile_push", {}).get("delivery_enabled"))
    active_notify_channels = [
        channel
        for channel, ready in (("telegram", telegram_ready), ("mobile_push", push_ready))
        if ready
    ]
    status_updates = {
        "news_worker": (
            "running" if news_ready else "degraded",
            {
                "note": news.get("note", "News provider status unavailable."),
                "provider_type": news.get("provider_type"),
                "events_count": news.get("events_count", 0),
                "risk_status": news.get("risk_status"),
            },
        ),
        "calendar_worker": (
            "running" if news_ready else "degraded",
            {
                "note": "Calendar ingestion is backed by the active news/calendar provider.",
                "provider_type": news.get("provider_type"),
                "events_count": news.get("events_count", 0),
            },
        ),
        "fundamental_analysis_worker": (
            "running" if news_ready else "waiting_news",
            {
                "note": "Fundamental analysis consumes normalized calendar/news events.",
                "news_risk_status": news.get("risk_status"),
            },
        ),
        "technical_analysis_worker": (
            "running" if enabled_pairs else "waiting_pairs",
            {"note": "Technical analysis runtime processes enabled pairs with candle, trend, and news risk overlay.", "enabled_pairs": enabled_pairs, "stale_pairs": stale_pairs},
        ),
        "risk_analysis_worker": ("ready", {"note": "Risk analysis rules are active in monitor-only mode."}),
        "data_validation_worker": ("ready", {"note": "Data validation gates are active for market/news quality checks."}),
        "signal_generation_worker": (
            "running" if enabled_pairs else "waiting_pairs",
            {
                "note": "Operator approved demo signal generation. Demo execution cycle now evaluates governed signals before MT5 handoff.",
                "enabled_pairs": enabled_pairs,
                "signal_records": latest_signals,
                "sent_executions": sent_executions,
                "blocked_executions": blocked_executions,
                "failed_executions": failed_executions,
            },
        ),
        "notification_worker": (
            "running" if active_notify_channels else "waiting_channels",
            {
                "note": (
                    f"Notification worker is active via {', '.join(active_notify_channels)}."
                    if active_notify_channels
                    else "Notification worker requires configured Telegram or Mobile Push credentials before delivery."
                ),
                "active_channels": active_notify_channels,
                "telegram_ready": telegram_ready,
                "mobile_push_ready": push_ready,
            },
        ),
    }
    for worker_id, (status, health) in status_updates.items():
        row = db.scalar(select(WorkerStatus).where(WorkerStatus.worker_id == worker_id))
        if not row:
            continue
        row.status = status
        row.last_run_at = now
        row.next_run_at = now + timedelta(minutes=5)
        row.health_json = health
        row.updated_at = now
    db.commit()


@router.get("/api/status")
def api_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    _seed_control_center(db)
    services = {
        "api": {"status": "ok"},
        "database": {"status": "ok"},
        "workers": {"status": "ok" if db.scalar(select(func.count()).select_from(WorkerStatus)) else "missing"},
        "calendar": {"status": "ok" if db.scalar(select(func.count()).select_from(DataSourceConfig).where(DataSourceConfig.source_type == "calendar")) else "missing"},
        "news": {"status": "ok"},
        "config": {"status": "ok"},
    }
    return {"status": "ok" if all(v["status"] == "ok" for v in services.values()) else "degraded", "services": services}


@router.get("/config/status")
def config_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    _seed_control_center(db)
    settings = [
        {
            "setting_key": row.setting_key,
            "setting_value": row.setting_value,
            "value_type": row.value_type,
            "category": row.category,
            "updated_at": _serialize_dt(row.updated_at),
        }
        for row in db.scalars(select(SystemSetting).order_by(SystemSetting.category, SystemSetting.setting_key)).all()
    ]
    return {"status": "ok", "settings": settings}


@router.put("/config/settings/{setting_key}")
def update_setting(setting_key: str, payload: SettingPayload, db: Session = Depends(get_db), principal=Depends(_require_admin)) -> dict[str, Any]:
    _seed_control_center(db)
    row = db.scalar(select(SystemSetting).where(SystemSetting.setting_key == setting_key))
    if not row:
        row = SystemSetting(setting_key=setting_key)
        db.add(row)
    row.setting_value = payload.setting_value
    row.value_type = payload.value_type
    row.category = payload.category
    row.updated_by = principal.user_id
    row.updated_at = _now()
    _audit(db, principal.user_id, "setting_update", "system_setting", setting_key, {"value_type": payload.value_type, "category": payload.category})
    db.commit()
    return {"status": "saved", "setting_key": setting_key}


@router.get("/data-sources")
def list_data_sources(db: Session = Depends(get_db)) -> dict[str, Any]:
    _seed_control_center(db)
    rows = db.scalars(select(DataSourceConfig).order_by(DataSourceConfig.source_type, DataSourceConfig.priority)).all()
    return {"items": [_source_dict(row) for row in rows]}


@router.put("/data-sources/{source_id}")
def update_data_source(source_id: str, payload: DataSourcePayload, db: Session = Depends(get_db), principal=Depends(_require_admin)) -> dict[str, Any]:
    _seed_control_center(db)
    row = db.scalar(select(DataSourceConfig).where(DataSourceConfig.source_id == source_id))
    if not row:
        row = DataSourceConfig(source_id=source_id)
        db.add(row)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    row.updated_at = _now()
    _audit(db, principal.user_id, "data_source_update", "data_source", source_id, {"source_type": payload.source_type, "provider": payload.provider})
    db.commit()
    return {"status": "saved", "source": _source_dict(row)}


@router.get("/calendar/status")
def calendar_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    _seed_control_center(db)
    total_events = db.scalar(select(func.count()).select_from(CalendarEvent)) or 0
    sources = db.scalars(select(DataSourceConfig).where(DataSourceConfig.source_type == "calendar").order_by(DataSourceConfig.priority)).all()
    last_success = db.scalar(select(func.max(DataSourceConfig.last_success_at)).where(DataSourceConfig.source_type == "calendar"))
    last_failure = db.scalar(select(func.max(DataSourceConfig.last_failure_at)).where(DataSourceConfig.source_type == "calendar"))
    return {
        "status": "ok" if any(source.enabled for source in sources) else "needs_configuration",
        "events_count": total_events,
        "enabled_sources": sum(1 for source in sources if source.enabled),
        "last_success_at": _serialize_dt(last_success),
        "last_failure_at": _serialize_dt(last_failure),
        "sources": [_source_dict(source) for source in sources],
    }


@router.get("/calendar/events")
def list_calendar_events(
    db: Session = Depends(get_db),
    currency: str | None = None,
    impact: str | None = None,
    source: str | None = None,
    keyword: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    query = select(CalendarEvent)
    count_query = select(func.count()).select_from(CalendarEvent)
    filters = []
    if currency:
        filters.append(CalendarEvent.currency == currency.upper())
    if impact:
        filters.append(CalendarEvent.impact == impact.lower())
    if source:
        filters.append(CalendarEvent.source_id == source)
    if status_filter:
        filters.append(CalendarEvent.status == status_filter)
    if keyword:
        filters.append(CalendarEvent.event_name.ilike(f"%{keyword}%"))
    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)
    total = db.scalar(count_query) or 0
    rows = db.scalars(query.order_by(CalendarEvent.event_time_utc.desc()).offset(offset).limit(limit)).all()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": [
            {
                "event_uid": row.event_uid,
                "source_id": row.source_id,
                "source": row.source,
                "event_time_utc": _serialize_dt(row.event_time_utc),
                "timezone": row.timezone,
                "currency": row.currency,
                "impact": row.impact,
                "event_name": row.event_name,
                "actual": row.actual,
                "forecast": row.forecast,
                "previous": row.previous,
                "revised": row.revised,
                "detail_url": row.detail_url,
                "status": row.status,
                "raw_json": row.raw_json,
                "normalized_json": row.normalized_json,
            }
            for row in rows
        ],
    }


@router.post("/calendar/scrape")
def manual_calendar_scrape(source_id: str | None = None, db: Session = Depends(get_db), principal=Depends(_require_admin)) -> dict[str, Any]:
    _seed_control_center(db)
    query = select(DataSourceConfig).where(DataSourceConfig.source_type == "calendar", DataSourceConfig.enabled.is_(True))
    if source_id:
        query = query.where(DataSourceConfig.source_id == source_id)
    sources = db.scalars(query.order_by(DataSourceConfig.priority)).all()
    if not sources:
        raise HTTPException(status_code=400, detail="No enabled calendar source is configured.")
    source = sources[0]
    provider = PROVIDERS.get(source.provider)
    if provider:
        result = provider.fetch(_now().date(), (_now() + timedelta(days=7)).date(), source.config_json or {})
        source.last_status = "ok" if result.ok else "adapter_pending"
        source.last_error = result.error
        if result.ok:
            source.last_success_at = _now()
        else:
            source.last_failure_at = _now()
    else:
        source.last_failure_at = _now()
        source.last_status = "adapter_missing"
        source.last_error = f"No provider adapter registered for {source.provider}."
    _audit(db, principal.user_id, "manual_calendar_scrape_requested", "data_source", source.source_id, {"provider": source.provider})
    db.commit()
    return {
        "status": "queued",
        "source_id": source.source_id,
        "provider": source.provider,
        "note": source.last_error,
    }


@router.get("/news/items")
def list_news_items(
    db: Session = Depends(get_db),
    keyword: str | None = None,
    currency: str | None = None,
    source: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    query = select(NewsItem)
    count_query = select(func.count()).select_from(NewsItem)
    filters = []
    if keyword:
        filters.append(or_(NewsItem.title.ilike(f"%{keyword}%"), NewsItem.summary.ilike(f"%{keyword}%")))
    if source:
        filters.append(NewsItem.source_id == source)
    if currency:
        filters.append(NewsItem.currencies.contains([currency.upper()]))
    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)
    total = db.scalar(count_query) or 0
    rows = db.scalars(query.order_by(NewsItem.published_at.desc().nullslast(), NewsItem.created_at.desc()).offset(offset).limit(limit)).all()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": [
            {
                "news_uid": row.news_uid,
                "source_id": row.source_id,
                "source": row.source,
                "published_at": _serialize_dt(row.published_at),
                "title": row.title,
                "summary": row.summary,
                "url": row.url,
                "currencies": row.currencies,
                "symbols": row.symbols,
                "sentiment": row.sentiment,
                "related_event_uid": row.related_event_uid,
            }
            for row in rows
        ],
    }


@router.get("/alert-rules")
def list_alert_rules(db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.scalars(select(AlertRule).order_by(AlertRule.created_at.desc())).all()
    return {
        "items": [
            {
                "rule_id": row.rule_id,
                "name": row.name,
                "enabled": row.enabled,
                "currencies": row.currencies,
                "impacts": row.impacts,
                "event_keywords": row.event_keywords,
                "exact_event_names": row.exact_event_names,
                "weekdays": row.weekdays,
                "sources": row.sources,
                "trading_pairs": row.trading_pairs,
                "minutes_before": row.minutes_before,
                "delivery_targets": row.delivery_targets,
                "severity": row.severity,
            }
            for row in rows
        ]
    }


@router.put("/alert-rules/{rule_id}")
def upsert_alert_rule(rule_id: str, payload: AlertRulePayload, db: Session = Depends(get_db), principal=Depends(_require_admin)) -> dict[str, Any]:
    row = db.scalar(select(AlertRule).where(AlertRule.rule_id == rule_id))
    if not row:
        row = AlertRule(rule_id=rule_id, created_by=principal.user_id)
        db.add(row)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    row.updated_at = _now()
    _audit(db, principal.user_id, "alert_rule_update", "alert_rule", rule_id, {"severity": payload.severity})
    db.commit()
    return {"status": "saved", "rule_id": rule_id}


@router.post("/alert-rules/{rule_id}/test")
def test_alert_rule(rule_id: str, db: Session = Depends(get_db), principal=Depends(_require_admin)) -> dict[str, Any]:
    row = db.scalar(select(AlertRule).where(AlertRule.rule_id == rule_id))
    if not row:
        raise HTTPException(status_code=404, detail="Alert rule not found.")
    delivery_id = f"test_{uuid.uuid4().hex[:16]}"
    db.add(
        AlertDeliveryHistory(
            delivery_id=delivery_id,
            rule_id=rule_id,
            target="dashboard",
            severity=row.severity,
            status="queued",
            message=f"Test alert for {row.name}",
        )
    )
    _audit(db, principal.user_id, "alert_rule_test", "alert_rule", rule_id)
    db.commit()
    return {"status": "queued", "delivery_id": delivery_id}


@router.get("/alert-rules/history")
def alert_delivery_history(db: Session = Depends(get_db), limit: int = Query(default=50, ge=1, le=500)) -> dict[str, Any]:
    rows = db.scalars(select(AlertDeliveryHistory).order_by(AlertDeliveryHistory.created_at.desc()).limit(limit)).all()
    return {
        "items": [
            {
                "delivery_id": row.delivery_id,
                "rule_id": row.rule_id,
                "event_uid": row.event_uid,
                "target": row.target,
                "severity": row.severity,
                "status": row.status,
                "message": row.message,
                "error": row.error,
                "created_at": _serialize_dt(row.created_at),
            }
            for row in rows
        ]
    }


@router.get("/workers/status")
def workers_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    _seed_control_center(db)
    _refresh_worker_runtime_status(db)
    rows = db.scalars(select(WorkerStatus).order_by(WorkerStatus.worker_type, WorkerStatus.worker_id)).all()
    run_rows = db.scalars(select(WorkerRun).order_by(WorkerRun.started_at.desc()).limit(500)).all()
    run_index: dict[str, dict[str, Any]] = {}
    for run in run_rows:
        bucket = run_index.setdefault(
            run.worker_id,
            {"latest": None, "latest_effective": None, "failed_runs": 0, "retry_runs": 0, "completed_runs": 0, "queued_runs": 0},
        )
        if bucket["latest"] is None:
            bucket["latest"] = run
        if bucket["latest_effective"] is None and run.status != "queued":
            bucket["latest_effective"] = run
        if run.status == "failed":
            bucket["failed_runs"] += 1
        if run.status == "retrying":
            bucket["retry_runs"] += 1
        if run.status == "completed":
            bucket["completed_runs"] += 1
        if run.status == "queued":
            bucket["queued_runs"] += 1
    return {
        "workers": [
            {
                "worker_id": row.worker_id,
                "name": row.name,
                "worker_type": row.worker_type,
                "status": row.status,
                "enabled": row.enabled,
                "last_run_at": _serialize_dt(row.last_run_at),
                "next_run_at": _serialize_dt(row.next_run_at),
                "duration_ms": row.duration_ms,
                "error_count": row.error_count,
                "retry_count": row.retry_count,
                "config_json": row.config_json,
                "health_json": row.health_json,
                "run_summary": (
                    (lambda bucket: {
                        "latest_run_id": ((bucket.get("latest_effective") or bucket.get("latest")).run_id if (bucket.get("latest_effective") or bucket.get("latest")) else None),
                        "latest_run_status": ((bucket.get("latest_effective") or bucket.get("latest")).status if (bucket.get("latest_effective") or bucket.get("latest")) else None),
                        "latest_run_started_at": _serialize_dt((bucket.get("latest_effective") or bucket.get("latest")).started_at) if (bucket.get("latest_effective") or bucket.get("latest")) else None,
                        "latest_run_finished_at": _serialize_dt((bucket.get("latest_effective") or bucket.get("latest")).finished_at) if (bucket.get("latest_effective") or bucket.get("latest")) else None,
                        "failed_runs": bucket.get("failed_runs", 0),
                        "retry_runs": bucket.get("retry_runs", 0),
                        "completed_runs": bucket.get("completed_runs", 0),
                        "queued_runs": bucket.get("queued_runs", 0),
                    })(run_index.get(row.worker_id, {}))
                ),
            }
            for row in rows
        ]
    }


@router.post("/workers/{worker_id}/{action}")
def worker_action(worker_id: str, action: str, db: Session = Depends(get_db), principal=Depends(_require_admin)) -> dict[str, Any]:
    if action not in {"start", "stop", "restart"}:
        raise HTTPException(status_code=400, detail="Invalid worker action.")
    _seed_control_center(db)
    row = db.scalar(select(WorkerStatus).where(WorkerStatus.worker_id == worker_id))
    if not row:
        raise HTTPException(status_code=404, detail="Worker not found.")
    now = _now()
    row.status = "running" if action in {"start", "restart"} else "stopped"
    row.updated_at = now
    run_id = f"{worker_id}_{uuid.uuid4().hex[:12]}"
    db.add(
        WorkerRun(
            run_id=run_id,
            worker_id=worker_id,
            status="completed",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            result_json={"requested_action": action, "applied_mode": "control_plane_runtime"},
        )
    )
    _audit(db, principal.user_id, f"worker_{action}_requested", "worker", worker_id)
    db.commit()
    return {"status": "applied", "worker_id": worker_id, "action": action, "run_id": run_id}


@router.get("/analysis/{analysis_type}/latest")
def latest_analysis(analysis_type: str, db: Session = Depends(get_db), symbol: str | None = None, limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    query = select(AnalysisSnapshot).where(AnalysisSnapshot.analysis_type == analysis_type)
    if symbol:
        query = query.where(AnalysisSnapshot.symbol == symbol.upper())
    rows = db.scalars(query.order_by(AnalysisSnapshot.created_at.desc()).limit(limit)).all()
    return {
        "analysis_type": analysis_type,
        "items": [
            {
                "snapshot_id": row.snapshot_id,
                "symbol": row.symbol,
                "timeframe": row.timeframe,
                "confidence": row.confidence,
                "status": row.status,
                "summary": row.summary,
                "inputs_json": row.inputs_json,
                "output_json": row.output_json,
                "created_at": _serialize_dt(row.created_at),
            }
            for row in rows
        ],
    }


@router.post("/analysis/{analysis_type}/seed-demo")
def seed_analysis_snapshot(analysis_type: str, db: Session = Depends(get_db), principal=Depends(_require_admin)) -> dict[str, Any]:
    if analysis_type not in {"technical", "fundamental"}:
        raise HTTPException(status_code=400, detail="analysis_type must be technical or fundamental")
    pairs = db.scalars(select(TradingPair).where(TradingPair.enabled.is_(True)).order_by(TradingPair.symbol.asc())).all()
    if not pairs:
        pairs = [TradingPair(symbol="EURUSD", default_timeframe="H1", enabled=True)]
    snapshot_ids: list[str] = []
    for pair in pairs:
        snapshot_id = f"{analysis_type}_{pair.symbol}_{uuid.uuid4().hex[:10]}"
        summary = (
            f"{pair.symbol} technical context prepared. Signals are still monitor-only and blocked from execution without approvals."
            if analysis_type == "technical"
            else f"{pair.symbol} fundamental context prepared from calendar/news. Risk gates remain active."
        )
        db.add(
            AnalysisSnapshot(
                snapshot_id=snapshot_id,
                analysis_type=analysis_type,
                symbol=pair.symbol,
                timeframe=(pair.default_timeframe or "H1"),
                confidence=0.0,
                status="scaffold_ready",
                summary=summary,
                inputs_json={"calendar_context": True, "news_context": True, "seeded": True},
                output_json={"note": "Connect worker runtime to produce live snapshots."},
            )
        )
        snapshot_ids.append(snapshot_id)
    _audit(db, principal.user_id, "analysis_snapshot_seeded", "analysis", analysis_type)
    db.commit()
    return {"status": "created", "analysis_type": analysis_type, "pairs": [pair.symbol for pair in pairs], "snapshot_ids": snapshot_ids}


@router.get("/logs/audit")
def audit_logs(
    db: Session = Depends(get_db),
    service: str | None = None,
    keyword: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    query = select(AuditLog)
    filters = []
    if service:
        filters.append(AuditLog.resource_type == service)
    if keyword:
        filters.append(or_(AuditLog.action.ilike(f"%{keyword}%"), AuditLog.resource_id.ilike(f"%{keyword}%"), AuditLog.note.ilike(f"%{keyword}%")))
    if filters:
        query = query.where(*filters)
    rows = db.scalars(query.order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return {
        "items": [
            {
                "actor": row.actor,
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "details": row.details,
                "note": row.note,
                "created_at": _serialize_dt(row.created_at),
            }
            for row in rows
        ]
    }
