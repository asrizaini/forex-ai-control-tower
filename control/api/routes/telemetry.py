from __future__ import annotations

import os
from ipaddress import ip_address, ip_network
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..control_schemas import AccountSnapshotOut, MarketSnapshotOut, WorkerTelemetryIn
from ..db import get_db
from ..models import AccountSnapshot, MarketSnapshot

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

PRIVATE_TELEMETRY_NETWORKS = (
    ip_network("10.10.1.0/24"),
    ip_network("127.0.0.0/8"),
)


@router.get("")
def list_resource() -> dict:
    return {
        "module": "telemetry",
        "description": "Persistent market/account snapshots from workers",
        "mode": "monitor-only-production",
    }


def _ingest_allowed(request: Request, x_telemetry_token: str | None) -> bool:
    expected = os.getenv("TELEMETRY_INGEST_TOKEN")
    if expected:
        return bool(x_telemetry_token) and x_telemetry_token == expected
    client_host = request.client.host if request.client else ""
    try:
        client_ip = ip_address(client_host)
    except ValueError:
        return False
    return any(client_ip in network for network in PRIVATE_TELEMETRY_NETWORKS)


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _persist_market_snapshots(db: Session, worker: str, result: dict[str, Any]) -> int:
    snapshots = result.get("snapshots", [])
    if not isinstance(snapshots, list):
        return 0
    count = 0
    for item in snapshots:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        db.add(
            MarketSnapshot(
                worker=worker,
                symbol=symbol,
                trend=str(item.get("trend", "unknown")),
                spread=_float_or_none(item.get("spread")),
                freshness_seconds=_int_or_none(item.get("freshness_seconds")),
                rates_count=int(item.get("rates_count") or 0),
                feed_fresh=bool(item.get("feed_fresh", False)),
                data_quality=str(result.get("data_quality", "limited")),
                payload_json=item,
            )
        )
        count += 1
    return count


def _persist_account_snapshot(db: Session, worker: str, result: dict[str, Any]) -> int:
    account = result.get("account", {})
    if not isinstance(account, dict) or not account:
        return 0
    db.add(
        AccountSnapshot(
            worker=worker,
            login_masked=str(account.get("login_masked", "***")),
            server=str(account.get("server", "unknown")),
            currency=str(account.get("currency", "unknown")),
            balance=_float_or_none(account.get("balance")),
            equity=_float_or_none(account.get("equity")),
            margin_free=_float_or_none(account.get("margin_free")),
            drawdown_pct=_float_or_none(account.get("drawdown_pct")),
            positions_count=int(result.get("positions_count") or 0),
            trade_allowed=_bool_or_none(account.get("trade_allowed")),
            risk_mode=str(result.get("risk_mode", "monitor_only")),
            auto_execution_enabled=bool(result.get("auto_execution_enabled", False)),
            payload_json={"account": account, "positions_count": result.get("positions_count", 0)},
        )
    )
    return 1


@router.post("/worker-snapshot", status_code=status.HTTP_202_ACCEPTED)
def ingest_worker_snapshot(
    payload: WorkerTelemetryIn,
    request: Request,
    x_telemetry_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if not _ingest_allowed(request, x_telemetry_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Telemetry ingest is restricted")
    worker = payload.worker
    result = payload.result
    market_count = _persist_market_snapshots(db, worker, result) if worker == "market" else 0
    account_count = _persist_account_snapshot(db, worker, result) if worker == "strategy_risk" else 0
    db.commit()
    return {"accepted": True, "market_snapshots": market_count, "account_snapshots": account_count}


@router.get("/market/latest", response_model=list[MarketSnapshotOut])
def latest_market_snapshots(symbol: str | None = None, limit: int = 50, db: Session = Depends(get_db)) -> list[MarketSnapshot]:
    query = select(MarketSnapshot).order_by(MarketSnapshot.created_at.desc()).limit(max(1, min(limit, 200)))
    if symbol:
        query = select(MarketSnapshot).where(MarketSnapshot.symbol == symbol.upper()).order_by(MarketSnapshot.created_at.desc()).limit(max(1, min(limit, 200)))
    return list(db.scalars(query))


@router.get("/accounts/latest", response_model=list[AccountSnapshotOut])
def latest_account_snapshots(limit: int = 50, db: Session = Depends(get_db)) -> list[AccountSnapshot]:
    query = select(AccountSnapshot).order_by(AccountSnapshot.created_at.desc()).limit(max(1, min(limit, 200)))
    return list(db.scalars(query))
