"""Data retention and automatic disk-space management.

Provides:
- Per-table retention policy configuration (days to keep)
- Manual and automatic cleanup of old records
- Disk-space monitoring and alerting
- VACUUM trigger after cleanup
"""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..models import HistoricalCandle, MarketSnapshot, SignalRecord
from ..time_utils import utcnow

router = APIRouter(prefix="/data-retention", tags=["data-retention"])

# ---------------------------------------------------------------------------
# Default retention policies (days).  Overridable via environment variables.
# ---------------------------------------------------------------------------
DEFAULT_RETENTION_DAYS: dict[str, int] = {
    "signal_records": int(os.getenv("RETENTION_SIGNAL_RECORDS_DAYS", "30")),
    "historical_candles": int(os.getenv("RETENTION_HISTORICAL_CANDLES_DAYS", "90")),
    "market_snapshots": int(os.getenv("RETENTION_MARKET_SNAPSHOTS_DAYS", "14")),
}

DISK_WARNING_PCT = float(os.getenv("DISK_WARNING_PCT", "80"))
DISK_CRITICAL_PCT = float(os.getenv("DISK_CRITICAL_PCT", "90"))
DISK_EMERGENCY_PCT = float(os.getenv("DISK_EMERGENCY_PCT", "95"))

TABLE_MODEL_MAP: dict[str, type] = {
    "signal_records": SignalRecord,
    "historical_candles": HistoricalCandle,
    "market_snapshots": MarketSnapshot,
}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class RetentionPolicyUpdate(BaseModel):
    table_name: str = Field(pattern=r"^(signal_records|historical_candles|market_snapshots)$")
    retention_days: int = Field(ge=1, le=3650)


class CleanupResult(BaseModel):
    table_name: str
    deleted_rows: int
    cutoff_date: str
    vacuum_ran: bool
    disk_before_pct: float | None = None
    disk_after_pct: float | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _disk_usage_pct(path: str = "/") -> float | None:
    """Return disk usage percentage for the given mount point."""
    try:
        usage = shutil.disk_usage(path)
        return round(usage.used / usage.total * 100, 1)
    except OSError:
        return None


def _pg_disk_usage_pct() -> float | None:
    """Return disk usage percentage for the PostgreSQL data directory.

    Falls back to '/' if the PGDATA env var is not set.
    """
    pg_data = os.getenv("PGDATA", "/")
    return _disk_usage_pct(pg_data)


def _run_vacuum(table_name: str) -> bool:
    """Run VACUUM (or VACUUM FULL on critical disk) on a specific table.

    VACUUM FULL requires an exclusive lock but reclaims all dead space.
    Regular VACUUM is lighter and runs concurrently.
    """
    disk_pct = _pg_disk_usage_pct()
    use_full = disk_pct is not None and disk_pct >= DISK_CRITICAL_PCT
    stmt = f"VACUUM FULL {table_name}" if use_full else f"VACUUM {table_name}"
    try:
        db = SessionLocal()
        try:
            db.execute(text(stmt))
            db.commit()
        finally:
            db.close()
        return True
    except Exception:
        return False


def _cleanup_table(table_name: str, retention_days: int, force_vacuum: bool = False) -> CleanupResult:
    """Delete records older than *retention_days* and optionally vacuum."""
    model = TABLE_MODEL_MAP.get(table_name)
    if model is None:
        return CleanupResult(table_name=table_name, deleted_rows=0, cutoff_date="", vacuum_ran=False)

    cutoff = utcnow() - timedelta(days=retention_days)
    cutoff_str = cutoff.isoformat()

    disk_before = _pg_disk_usage_pct()

    db = SessionLocal()
    try:
        # Count rows to delete first (for reporting)
        count_result = db.scalar(
            select(func.count()).select_from(model).where(model.created_at < cutoff)
        )
        deleted_rows = count_result or 0

        if deleted_rows > 0:
            db.execute(model.__table__.delete().where(model.created_at < cutoff))
            db.commit()
    finally:
        db.close()

    # Vacuum after deletion if rows were removed or forced
    vacuum_ran = False
    if deleted_rows > 0 or force_vacuum:
        vacuum_ran = _run_vacuum(table_name)

    disk_after = _pg_disk_usage_pct()

    return CleanupResult(
        table_name=table_name,
        deleted_rows=deleted_rows,
        cutoff_date=cutoff_str,
        vacuum_ran=vacuum_ran,
        disk_before_pct=disk_before,
        disk_after_pct=disk_after,
    )


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@router.get("")
def list_resource() -> dict:
    return {
        "module": "data-retention",
        "description": "Automatic disk-space management, data retention policies, and cleanup",
        "mode": "active",
    }


@router.get("/policies")
def get_retention_policies() -> dict:
    """Return current retention policies for all managed tables."""
    policies = {}
    for table_name, days in DEFAULT_RETENTION_DAYS.items():
        model = TABLE_MODEL_MAP[table_name]
        db = SessionLocal()
        try:
            total = db.scalar(select(func.count()).select_from(model)) or 0
            cutoff = utcnow() - timedelta(days=days)
            expirable = db.scalar(
                select(func.count()).select_from(model).where(model.created_at < cutoff)
            ) or 0
        finally:
            db.close()
        policies[table_name] = {
            "retention_days": days,
            "total_rows": total,
            "expirable_rows": expirable,
        }
    return {
        "policies": policies,
        "disk_usage_pct": _pg_disk_usage_pct(),
        "disk_status": _disk_status_label(),
    }


@router.put("/policies")
def update_retention_policy(payload: RetentionPolicyUpdate) -> dict:
    """Update retention days for a specific table (in-memory; set env vars for persistence)."""
    DEFAULT_RETENTION_DAYS[payload.table_name] = payload.retention_days
    return {
        "table_name": payload.table_name,
        "retention_days": payload.retention_days,
        "note": "Policy updated in memory. Set RETENTION_<TABLE>_DAYS env var for persistence across restarts.",
    }


@router.post("/cleanup")
def run_cleanup(
    table_name: str | None = Query(default=None, description="Specific table to clean, or omit for all"),
    force_vacuum: bool = Query(default=False, description="Force VACUUM even if no rows deleted"),
) -> dict:
    """Execute data retention cleanup.  Runs automatically via systemd timer."""
    tables = [table_name] if table_name else list(TABLE_MODEL_MAP.keys())
    results = []
    for tbl in tables:
        if tbl not in TABLE_MODEL_MAP:
            continue
        retention_days = DEFAULT_RETENTION_DAYS.get(tbl, 30)
        result = _cleanup_table(tbl, retention_days, force_vacuum=force_vacuum)
        results.append(result.model_dump())
    return {
        "cleanup_results": results,
        "disk_usage_pct": _pg_disk_usage_pct(),
        "disk_status": _disk_status_label(),
    }


@router.get("/disk-status")
def disk_status() -> dict:
    """Return current disk usage and alert level."""
    pct = _pg_disk_usage_pct()
    root_pct = _disk_usage_pct("/")
    return {
        "postgres_disk_pct": pct,
        "root_disk_pct": root_pct,
        "status": _disk_status_label(),
        "thresholds": {
            "warning": DISK_WARNING_PCT,
            "critical": DISK_CRITICAL_PCT,
            "emergency": DISK_EMERGENCY_PCT,
        },
        "auto_cleanup_enabled": True,
        "recommendation": _disk_recommendation(pct),
    }


@router.post("/emergency-purge")
def emergency_purge(
    table_name: str = Query(description="Table to emergency-purge (truncates all data)"),
) -> dict:
    """Emergency: TRUNCATE a table to reclaim disk space immediately.

    Only use when disk is critically full and regular cleanup is insufficient.
    """
    if table_name not in TABLE_MODEL_MAP:
        return {"error": f"Unknown table: {table_name}. Allowed: {list(TABLE_MODEL_MAP.keys())}"}

    disk_before = _pg_disk_usage_pct()
    db = SessionLocal()
    try:
        db.execute(text(f"TRUNCATE TABLE {table_name}"))
        db.commit()
    finally:
        db.close()

    vacuum_ran = _run_vacuum(table_name)
    disk_after = _pg_disk_usage_pct()

    return {
        "action": "emergency_purge",
        "table_name": table_name,
        "vacuum_ran": vacuum_ran,
        "disk_before_pct": disk_before,
        "disk_after_pct": disk_after,
        "disk_status": _disk_status_label(),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _disk_status_label() -> str:
    pct = _pg_disk_usage_pct()
    if pct is None:
        return "unknown"
    if pct >= DISK_EMERGENCY_PCT:
        return "emergency"
    if pct >= DISK_CRITICAL_PCT:
        return "critical"
    if pct >= DISK_WARNING_PCT:
        return "warning"
    return "healthy"


def _disk_recommendation(pct: float | None) -> str:
    if pct is None:
        return "Unable to read disk usage. Check mount permissions."
    if pct >= DISK_EMERGENCY_PCT:
        return "EMERGENCY: Disk nearly full. Emergency purge recommended via /data-retention/emergency-purge."
    if pct >= DISK_CRITICAL_PCT:
        return "CRITICAL: Disk space critically low. Run cleanup immediately via /data-retention/cleanup."
    if pct >= DISK_WARNING_PCT:
        return "WARNING: Disk usage above threshold. Consider running /data-retention/cleanup to free space."
    return "Disk usage is within normal range."


def auto_cleanup_if_needed() -> dict | None:
    """Check disk usage and run automatic cleanup if above warning threshold.

    Called by the systemd timer / worker script.
    Returns cleanup results if cleanup was triggered, None otherwise.
    """
    pct = _pg_disk_usage_pct()
    if pct is None or pct < DISK_WARNING_PCT:
        return None

    # Run cleanup on all tables, starting with the one with shortest retention
    priority_order = sorted(TABLE_MODEL_MAP.keys(), key=lambda t: DEFAULT_RETENTION_DAYS.get(t, 999))
    results = []
    for tbl in priority_order:
        retention_days = DEFAULT_RETENTION_DAYS.get(tbl, 30)
        result = _cleanup_table(tbl, retention_days, force_vacuum=(pct >= DISK_CRITICAL_PCT))
        results.append(result.model_dump())

    # Check if still critical after cleanup
    new_pct = _pg_disk_usage_pct()
    if new_pct is not None and new_pct >= DISK_CRITICAL_PCT:
        # Aggressive: reduce retention by half and re-run
        for tbl in priority_order:
            original_days = DEFAULT_RETENTION_DAYS.get(tbl, 30)
            reduced_days = max(original_days // 2, 1)
            result = _cleanup_table(tbl, reduced_days, force_vacuum=True)
            results.append({**result.model_dump(), "note": "aggressive_half_retention"})

    return {
        "trigger": "auto_cleanup",
        "disk_before_pct": pct,
        "disk_after_pct": _pg_disk_usage_pct(),
        "disk_status": _disk_status_label(),
        "cleanup_results": results,
    }