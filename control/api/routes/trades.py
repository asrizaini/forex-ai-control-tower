from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address, ip_network
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from execution_guard.control_plane import ExecutionTelemetry, evaluate_control_plane_policy
from execution_guard.exposure import evaluate_exposure
from execution_guard.approval_token import create_approval_token
from execution_guard.guard import approve_execution
from execution_guard.schemas import ExecutionRequest
from news_feed.adapter import evaluate_news_status

from ..credential_store import runtime_bool, runtime_float, runtime_int, runtime_value
from ..crud import audit
from ..db import get_db
from ..dependencies import current_principal
from ..models import (
    Account,
    AccountSnapshot,
    KillSwitch,
    MarketSnapshot,
    RiskPolicy,
    SignalRecord,
    Strategy,
    LlmUsage,
    TradeExecution,
    TradingPair,
)
from ..permissions import has_permission
from ..time_utils import format_local, iso_local
from .trading import _build_pair_summary, _generate_signal_for_summary

router = APIRouter(prefix="/trades", tags=["trades"])

PRIVATE_EXECUTION_NETWORKS = (
    ip_network("10.10.1.0/24"),
    ip_network("127.0.0.0/8"),
)


@router.get("")
def list_resource(db: Session = Depends(get_db)) -> dict:
    latest = db.scalar(select(TradeExecution).order_by(TradeExecution.created_at.desc()).limit(1))
    total = db.scalar(select(func.count()).select_from(TradeExecution)) or 0
    sent = db.scalar(select(func.count()).select_from(TradeExecution).where(TradeExecution.status == "sent")) or 0
    blocked = db.scalar(select(func.count()).select_from(TradeExecution).where(TradeExecution.status == "blocked")) or 0
    failed = db.scalar(select(func.count()).select_from(TradeExecution).where(TradeExecution.status == "failed")) or 0
    return {
        "module": "trades",
        "description": "Trade journal and governed demo execution state",
        "mode": "production-required",
        "summary": {
            "total": total,
            "sent": sent,
            "blocked": blocked,
            "failed": failed,
            "last_execution_at": iso_local(latest.created_at) if latest else None,
            "last_status": latest.status if latest else None,
        },
    }


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bridge_base_url() -> str:
    return runtime_value("MT5_BRIDGE_API_URL", "http://10.10.1.86:8501").rstrip("/")


def _bridge_token() -> str:
    token = runtime_value("BRIDGE_API_TOKEN")
    if not token:
        raise RuntimeError("BRIDGE_API_TOKEN is not configured")
    return token


def _guard_enabled_for_demo() -> bool:
    return runtime_bool("DEMO_GUARD_ENABLED", False)


def _bridge_request(method: str, path: str, payload: dict[str, Any] | None = None, guard_token: str | None = None) -> dict[str, Any]:
    url = f"{_bridge_base_url()}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    request.add_header("X-Bridge-Token", _bridge_token())
    if guard_token:
        request.add_header("X-Execution-Guard-Token", guard_token)
    try:
        with urllib.request.urlopen(request, timeout=max(4, runtime_int("DEMO_EXECUTION_BRIDGE_TIMEOUT_SECONDS", 8))) as response:
            text = response.read().decode("utf-8", errors="replace")
            return {"ok": 200 <= response.status < 400, "status": response.status, "body": json.loads(text) if text else {}}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(text) if text else {}
        except json.JSONDecodeError:
            body = {"detail": text or "http_error"}
        return {"ok": False, "status": exc.code, "body": body}
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": 0, "body": {"detail": type(exc).__name__}}


def _runner_allowed(request: Request, x_runner_token: str | None) -> bool:
    expected = runtime_value("DEMO_EXECUTION_RUNNER_TOKEN") or runtime_value("TELEMETRY_INGEST_TOKEN")
    if expected:
        return bool(x_runner_token) and x_runner_token == expected
    client_host = request.client.host if request.client else ""
    try:
        client_ip = ip_address(client_host)
    except ValueError:
        return False
    return any(client_ip in network for network in PRIVATE_EXECUTION_NETWORKS)


def _active_demo_account(db: Session, account_id: str | None = None) -> Account | None:
    if account_id:
        return db.scalar(
            select(Account)
            .where(Account.account_id == account_id, Account.enabled.is_(True), Account.environment == "demo")
            .limit(1)
        )
    return db.scalar(
        select(Account)
        .where(Account.enabled.is_(True), Account.environment == "demo")
        .order_by(Account.created_at.asc())
        .limit(1)
    )


def _latest_signal_for_pair(db: Session, symbol: str, timeframe: str) -> SignalRecord | None:
    return db.scalar(
        select(SignalRecord)
        .where(SignalRecord.symbol == symbol, SignalRecord.timeframe == timeframe)
        .order_by(SignalRecord.created_at.desc())
        .limit(1)
    )


def _latest_market_snapshot(db: Session, symbol: str, timeframe: str) -> MarketSnapshot | None:
    candidates = list(
        db.scalars(select(MarketSnapshot).where(MarketSnapshot.symbol == symbol).order_by(MarketSnapshot.created_at.desc()).limit(12))
    )
    for item in candidates:
        payload = item.payload_json or {}
        if str(payload.get("timeframe", "")).upper() == timeframe.upper():
            return item
    return candidates[0] if candidates else None


def _has_active_kill_switch(db: Session, account_id: str, symbol: str, strategy_id: str | None) -> bool:
    scopes = [
        and_(KillSwitch.scope == "global", KillSwitch.active.is_(True)),
        and_(KillSwitch.scope == "demo", KillSwitch.active.is_(True)),
        and_(KillSwitch.scope == "account", KillSwitch.active.is_(True), KillSwitch.target_id == account_id),
        and_(KillSwitch.scope == "symbol", KillSwitch.active.is_(True), KillSwitch.target_id == symbol),
    ]
    if strategy_id:
        scopes.append(and_(KillSwitch.scope == "strategy", KillSwitch.active.is_(True), KillSwitch.target_id == strategy_id))
    return db.scalar(select(KillSwitch.id).where(or_(*scopes)).limit(1)) is not None


def _open_positions_for_symbol(positions_payload: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
    return [item for item in positions_payload if str(item.get("symbol", "")).upper() == symbol.upper()]


def _recent_sent_exists(db: Session, account_id: str, symbol: str, timeframe: str, cooldown_minutes: int) -> bool:
    cutoff = _now_utc() - timedelta(minutes=max(1, cooldown_minutes))
    return (
        db.scalar(
            select(TradeExecution.id).where(
                TradeExecution.account_id == account_id,
                TradeExecution.symbol == symbol,
                TradeExecution.timeframe == timeframe,
                TradeExecution.status == "sent",
                TradeExecution.created_at >= cutoff,
            ).limit(1)
        )
        is not None
    )


def _eligible_signal_rows(db: Session, max_age_minutes: int) -> list[tuple[TradingPair, str, SignalRecord]]:
    rows: list[tuple[TradingPair, str, SignalRecord]] = []
    cutoff = _now_utc() - timedelta(minutes=max_age_minutes)
    enabled_pairs = list(db.scalars(select(TradingPair).where(TradingPair.enabled.is_(True)).order_by(TradingPair.symbol.asc())))
    for pair in enabled_pairs:
        metadata = pair.metadata_json or {}
        configured = metadata.get("analysis_timeframes") if isinstance(metadata.get("analysis_timeframes"), list) else []
        timeframes: list[str] = []
        for item in configured:
            tf = str(item).upper().strip()
            if tf and tf not in timeframes:
                timeframes.append(tf)
        default_tf = str(pair.default_timeframe or "M1").upper()
        if default_tf not in timeframes:
            timeframes.insert(0, default_tf)
        for timeframe in timeframes:
            signal = _latest_signal_for_pair(db, pair.symbol, timeframe)
            if not signal:
                continue
            if signal.created_at < cutoff:
                continue
            if signal.direction not in {"buy", "sell"}:
                continue
            if signal.signal_status in {"blocked", "stale", "no_signal"}:
                continue
            rows.append((pair, timeframe, signal))
    return rows


def _refresh_signals_for_enabled_pairs(db: Session) -> int:
    enabled_pairs = list(db.scalars(select(TradingPair).where(TradingPair.enabled.is_(True)).order_by(TradingPair.symbol.asc())))
    generated = 0
    for pair in enabled_pairs:
        summary = _build_pair_summary(db, pair)
        timeframes = summary.get("configured_timeframes", [summary.get("timeframe", "M1")])
        for timeframe in timeframes:
            tf_upper = str(timeframe).upper()
            tf_row = next((item for item in summary.get("timeframe_breakdown", []) if str(item.get("timeframe", "")).upper() == tf_upper), None)
            tf_summary = dict(summary)
            tf_summary["timeframe"] = tf_upper
            if tf_row:
                tf_summary["candle_summary"] = tf_row.get("candle_summary", summary.get("candle_summary"))
                tf_summary["trend_status"] = tf_row.get("trend_status", summary.get("trend_status"))
                tf_summary["current_bias"] = tf_row.get("bias", summary.get("current_bias"))
                tf_summary["data_freshness_status"] = tf_row.get("freshness", summary.get("data_freshness_status"))
            _generate_signal_for_summary(db, tf_summary, pair.assigned_strategy_id)
            generated += 1
        pair.last_processed_at = _now_utc()
        pair.status = "processed"
        pair.updated_at = _now_utc()
    return generated


def _create_execution_row(
    db: Session,
    account_id: str,
    pair: TradingPair,
    timeframe: str,
    signal: SignalRecord,
    status: str,
    reason: str,
    guard_checks: dict[str, Any] | None = None,
    mt5_check: dict[str, Any] | None = None,
    mt5_send: dict[str, Any] | None = None,
) -> TradeExecution:
    row = TradeExecution(
        execution_id=f"exec_{secrets.token_hex(10)}",
        account_id=account_id,
        symbol=pair.symbol,
        timeframe=timeframe,
        strategy_id=pair.assigned_strategy_id,
        signal_id=signal.signal_id,
        direction=signal.direction,
        volume=runtime_float("DEMO_EXECUTION_LOT_SIZE", 0.01),
        status=status,
        reason=reason,
        guard_checks_json=guard_checks or {},
        mt5_check_json=mt5_check or {},
        mt5_send_json=mt5_send or {},
    )
    db.add(row)
    return row


def _strategy_allowed_for_demo_auto(db: Session, strategy_id: str | None) -> bool:
    if not strategy_id:
        return False
    strategy = db.scalar(select(Strategy).where(Strategy.strategy_id == strategy_id).limit(1))
    if not strategy:
        return False
    return strategy.lifecycle_state in {"approved_for_demo_auto", "approved_for_manual", "approved_for_live_restricted", "demo_testing"}


def _build_guard_result(
    db: Session,
    account: Account,
    pair: TradingPair,
    timeframe: str,
    signal: SignalRecord,
    positions_payload: list[dict[str, Any]],
) -> tuple[bool, dict[str, Any]]:
    latest_account = db.scalar(select(AccountSnapshot).order_by(AccountSnapshot.created_at.desc()).limit(1))
    market = _latest_market_snapshot(db, pair.symbol, timeframe)
    market_payload = market.payload_json if market else {}
    news = signal.analysis_json.get("news_status") if isinstance(signal.analysis_json, dict) else {}
    if not isinstance(news, dict) or not news:
        news = evaluate_news_status(pair.symbol)
    spread = _as_float(market_payload.get("spread"), _as_float(market.spread if market else None, 0.0))
    slippage = runtime_float("DEMO_EXECUTION_MAX_SLIPPAGE_POINTS_RUNTIME", 0.0)
    open_positions = _open_positions_for_symbol(positions_payload, pair.symbol)
    pending_signals = []
    exposure = evaluate_exposure(
        symbol=pair.symbol,
        side=signal.direction.upper(),
        account_id=account.account_id,
        strategy_id=pair.assigned_strategy_id or "",
        open_positions=open_positions,
        pending_signals=pending_signals,
        max_same_symbol_positions=runtime_int("DEMO_EXECUTION_MAX_SAME_SYMBOL_POSITIONS", 1),
        max_correlated_positions=runtime_int("DEMO_EXECUTION_MAX_CORRELATED_POSITIONS", 3),
    )
    telemetry = ExecutionTelemetry(
        daily_loss_pct=_as_float(latest_account.drawdown_pct if latest_account else 0.0, 0.0),
        weekly_loss_pct=_as_float(latest_account.drawdown_pct if latest_account else 0.0, 0.0),
        open_trades=len(positions_payload),
        trades_today=_as_int(
            db.scalar(
                select(func.count()).select_from(TradeExecution).where(
                    TradeExecution.account_id == account.account_id,
                    TradeExecution.status == "sent",
                    TradeExecution.created_at >= (_now_utc() - timedelta(days=1)),
                )
            ),
            0,
        ),
        spread_points=spread,
        slippage_points=slippage,
        market_data_quality_ok=bool(market and market.feed_fresh),
        broker_compatibility_ok=runtime_bool("DEMO_EXECUTION_ASSUME_BROKER_COMPATIBLE", True),
        margin_available=_as_float(latest_account.margin_free if latest_account else 0.0, 0.0) > 0.0,
        duplicate_trade_risk=bool(open_positions),
        correlation_exposure_ok=runtime_bool("DEMO_EXECUTION_ASSUME_CORRELATION_OK", True) and exposure.correlation_exposure_ok,
        news_halt_active=bool(news.get("news_halt_active", True)),
    )
    request = ExecutionRequest(
        user_id=runtime_value("DEMO_EXECUTION_USER_ID", "system"),
        account_id=account.account_id,
        strategy_id=pair.assigned_strategy_id or "unassigned_strategy",
        symbol=pair.symbol,
        side=signal.direction.upper(),
        volume=runtime_float("DEMO_EXECUTION_LOT_SIZE", 0.01),
        environment=account.environment,
        trading_mode=account.trading_mode,
        live_order=False,
        manual_approval=runtime_bool("DEMO_EXECUTION_MANUAL_APPROVAL_BYPASS", True),
        order_check_passed=True,
        system_health_score=runtime_int("DEMO_EXECUTION_SYSTEM_HEALTH_SCORE", 90),
        kill_switch_active=_has_active_kill_switch(db, account.account_id, pair.symbol, pair.assigned_strategy_id),
    )
    policy = evaluate_control_plane_policy(db, request, telemetry)
    checks = dict(policy.checks)
    if runtime_bool("DEMO_EXECUTION_ASSUME_PERMISSIONS", True):
        checks["user_permission"] = True
        checks["account_permission"] = True
        checks["strategy_permission"] = True
    guarded_request = ExecutionRequest(
        **{
            **request.__dict__,
            "environment": policy.effective_environment,
            "trading_mode": policy.effective_trading_mode,
            "checks": checks,
        }
    )
    decision = approve_execution(guarded_request)
    decision_payload = {
        "approved": decision.approved,
        "reasons": list(decision.reasons),
        "checks": checks,
        "policy_reasons": list(policy.reasons),
        "exposure_reasons": list(exposure.reasons),
        "effective_environment": policy.effective_environment,
        "effective_trading_mode": policy.effective_trading_mode,
        "strategy_id": pair.assigned_strategy_id,
        "signal_id": signal.signal_id,
        "token": decision.token if decision.approved else None,
    }
    return decision.approved, decision_payload


def _execute_one_signal(db: Session, account: Account, pair: TradingPair, timeframe: str, signal: SignalRecord, positions_payload: list[dict[str, Any]]) -> TradeExecution:
    if account.trading_mode != "demo_auto":
        return _create_execution_row(db, account.account_id, pair, timeframe, signal, "blocked", "account_not_in_demo_auto_mode")
    if not _strategy_allowed_for_demo_auto(db, pair.assigned_strategy_id):
        return _create_execution_row(db, account.account_id, pair, timeframe, signal, "blocked", "strategy_not_approved_for_demo_auto")
    if _recent_sent_exists(db, account.account_id, pair.symbol, timeframe, runtime_int("DEMO_EXECUTION_COOLDOWN_MINUTES", 15)):
        return _create_execution_row(db, account.account_id, pair, timeframe, signal, "skipped", "cooldown_active")

    approved, guard_payload = _build_guard_result(db, account, pair, timeframe, signal, positions_payload)
    guard_enabled = _guard_enabled_for_demo()
    if not guard_enabled:
        advisory_reasons = list(guard_payload.get("reasons") or [])
        guard_payload["guard_mode"] = "disabled"
        guard_payload["guard_would_block"] = not approved
        guard_payload["advisory_reasons"] = advisory_reasons
        guard_payload["approved"] = True
        guard_payload["token"] = create_approval_token(
            account.account_id,
            pair.assigned_strategy_id or "unassigned_strategy",
            ttl_seconds=max(30, runtime_int("DEMO_EXECUTION_GUARD_TOKEN_TTL_SECONDS", 60)),
        )
    elif not approved:
        reason = ", ".join(guard_payload.get("reasons") or ["execution_guard_blocked"])
        return _create_execution_row(db, account.account_id, pair, timeframe, signal, "blocked", reason, guard_checks=guard_payload)

    volume = runtime_float("DEMO_EXECUTION_LOT_SIZE", 0.01)
    side = signal.direction.upper()
    order_payload = {
        "client_order_id": f"{signal.signal_id}_{secrets.token_hex(4)}",
        "account_id": account.account_id,
        "symbol": pair.symbol,
        "side": side,
        "volume": volume,
        "live_order": False,
        "deviation": runtime_int("DEMO_EXECUTION_DEVIATION", 20),
    }
    check_result = _bridge_request("POST", "/order/check", payload=order_payload)
    check_body = check_result.get("body", {})
    check_passed = bool(check_body.get("check_passed"))
    if not check_result.get("ok") or not check_passed:
        reason = check_body.get("detail") or "mt5_order_check_failed"
        return _create_execution_row(
            db,
            account.account_id,
            pair,
            timeframe,
            signal,
            "failed",
            str(reason),
            guard_checks=guard_payload,
            mt5_check=check_body if isinstance(check_body, dict) else {"detail": str(check_body)},
        )

    send_result = _bridge_request(
        "POST",
        "/order/send",
        payload=order_payload,
        guard_token=guard_payload.get("token"),
    )
    send_body = send_result.get("body", {})
    if not send_result.get("ok"):
        reason = send_body.get("detail") if isinstance(send_body, dict) else "mt5_order_send_failed"
        return _create_execution_row(
            db,
            account.account_id,
            pair,
            timeframe,
            signal,
            "failed",
            str(reason),
            guard_checks=guard_payload,
            mt5_check=check_body if isinstance(check_body, dict) else {"detail": str(check_body)},
            mt5_send=send_body if isinstance(send_body, dict) else {"detail": str(send_body)},
        )
    return _create_execution_row(
        db,
        account.account_id,
        pair,
        timeframe,
        signal,
        "sent",
        "demo_order_sent",
        guard_checks=guard_payload,
        mt5_check=check_body if isinstance(check_body, dict) else {"detail": str(check_body)},
        mt5_send=send_body if isinstance(send_body, dict) else {"detail": str(send_body)},
    )


def _map_mt5_trade_mode(value: Any) -> str:
    if isinstance(value, bool):
        return "demo" if value else "unknown"
    normalized = str(value).lower()
    if normalized in {"0", "demo", "trade_mode_demo"}:
        return "demo"
    if normalized in {"2", "real", "trade_mode_real"}:
        return "real"
    return "unknown"


def _latest_llm_usage(db: Session) -> dict[str, Any]:
    row = db.scalar(select(LlmUsage).order_by(LlmUsage.created_at.desc()).limit(1))
    today_cutoff = _now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
    today_requests = db.scalar(select(func.count()).select_from(LlmUsage).where(LlmUsage.created_at >= today_cutoff)) or 0
    today_cost = db.scalar(select(func.coalesce(func.sum(LlmUsage.estimated_cost), 0.0)).where(LlmUsage.created_at >= today_cutoff)) or 0.0
    return {
        "today_requests": int(today_requests),
        "today_estimated_cost": float(today_cost),
        "last_provider": row.provider if row else None,
        "last_task_type": row.task_type if row else None,
        "last_used_at": iso_local(row.created_at) if row else None,
        "optimization_note": "LLM calls are avoided during normal status refresh. Rules and cached analysis are reused unless you run manual/orchestrator AI actions.",
    }


def _execution_cycle_status(account: Account | None, latest_execution: TradeExecution | None, bridge_ok: bool) -> str:
    if not account:
        return "error"
    if account.trading_mode != "demo_auto":
        return "stopped"
    if not bridge_ok:
        return "error"
    if not latest_execution:
        return "idle"
    if latest_execution.status == "sent":
        return "monitoring_trade"
    if latest_execution.status in {"blocked", "skipped"}:
        return "waiting_for_signal"
    if latest_execution.status == "failed":
        return "error"
    return "analyzing"


@router.get("/demo-auto/status")
def demo_auto_status(principal=Depends(current_principal), db: Session = Depends(get_db)) -> dict[str, Any]:
    if not has_permission(principal.role, "risk:read"):
        raise HTTPException(status_code=403, detail="Permission denied")
    account = _active_demo_account(db, runtime_value("DEMO_EXECUTION_ACCOUNT_ID", "demo_main"))
    latest_execution = db.scalar(select(TradeExecution).order_by(TradeExecution.created_at.desc()).limit(1))
    latest_snapshot = db.scalar(select(AccountSnapshot).order_by(AccountSnapshot.created_at.desc()).limit(1))
    enabled_pairs = list(db.scalars(select(TradingPair).where(TradingPair.enabled.is_(True)).order_by(TradingPair.symbol.asc())))
    bridge_health = _bridge_request("GET", "/health")
    bridge_account = _bridge_request("GET", "/account")
    positions_result = _bridge_request("GET", "/positions")
    pending_result = _bridge_request("GET", "/history")
    positions = positions_result.get("body", {}).get("positions", []) if positions_result.get("ok") else []
    history = pending_result.get("body", {}).get("history", []) if pending_result.get("ok") else []
    if not isinstance(positions, list):
        positions = []
    if not isinstance(history, list):
        history = []
    bridge_ok = bool(bridge_health.get("ok")) and bool(bridge_health.get("body", {}).get("mt5_connected"))
    account_body = bridge_account.get("body", {}) if isinstance(bridge_account.get("body"), dict) else {}
    account_type = _map_mt5_trade_mode(account_body.get("trade_mode"))
    mode = account.trading_mode if account else "monitor_only"
    guard_enabled = _guard_enabled_for_demo()
    status_payload = {
        "mode": "demo" if account else "disabled",
        "guard_enabled": guard_enabled,
        "guard_note": (
            "Execution Guard is active and can block order_send."
            if guard_enabled
            else "Execution Guard blocking is temporarily disabled for demo flow. Advisory checks are still logged."
        ),
        "mt5_connected": bridge_ok,
        "mt5_bridge_health": bridge_health.get("body", {}),
        "account_type": account_type,
        "account_id": account.account_id if account else None,
        "auto_trade_status": "running" if mode == "demo_auto" else "stopped",
        "cycle_status": _execution_cycle_status(account, latest_execution, bridge_ok),
        "active_pair": latest_execution.symbol if latest_execution else (enabled_pairs[0].symbol if enabled_pairs else None),
        "active_timeframe": latest_execution.timeframe if latest_execution else (enabled_pairs[0].default_timeframe if enabled_pairs else None),
        "last_action": latest_execution.reason if latest_execution else "No execution action yet.",
        "last_update_local": format_local(latest_execution.created_at) if latest_execution else format_local(_now_utc()),
        "account_snapshot": {
            "balance": latest_snapshot.balance if latest_snapshot else None,
            "equity": latest_snapshot.equity if latest_snapshot else None,
            "margin_free": latest_snapshot.margin_free if latest_snapshot else None,
            "positions_count": latest_snapshot.positions_count if latest_snapshot else len(positions),
            "trade_allowed": latest_snapshot.trade_allowed if latest_snapshot else account_body.get("trade_allowed"),
        },
        "execution_confirmation": {
            "dashboard_can_place_demo_orders": mode == "demo_auto" and bridge_ok and account_type != "real",
            "bridge_mode": bridge_health.get("body", {}).get("bridge_mode", "unknown"),
            "last_order_attempt": {
                "execution_id": latest_execution.execution_id if latest_execution else None,
                "symbol": latest_execution.symbol if latest_execution else None,
                "status": latest_execution.status if latest_execution else None,
                "reason": latest_execution.reason if latest_execution else None,
                "created_at": format_local(latest_execution.created_at) if latest_execution else None,
            },
            "open_positions_count": len(positions),
            "history_count": len(history),
        },
        "enabled_pairs": [pair.symbol for pair in enabled_pairs],
        "enabled_timeframes": sorted({str(pair.default_timeframe or "M1").upper() for pair in enabled_pairs}),
        "llm_usage": _latest_llm_usage(db),
    }
    return status_payload


@router.get("/demo-auto/activity")
def demo_auto_activity(
    limit: int = Query(default=40, ge=5, le=200),
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not has_permission(principal.role, "risk:read"):
        raise HTTPException(status_code=403, detail="Permission denied")
    account = _active_demo_account(db, runtime_value("DEMO_EXECUTION_ACCOUNT_ID", "demo_main"))
    events: list[dict[str, Any]] = []
    bridge_health = _bridge_request("GET", "/health")
    bridge_ok = bool(bridge_health.get("ok")) and bool(bridge_health.get("body", {}).get("mt5_connected"))
    events.append(
        {
            "step": "mt5_connection",
            "status": "ok" if bridge_ok else "error",
            "message": "Connected to MT5 demo bridge." if bridge_ok else "MT5 bridge is unavailable or not connected.",
            "timestamp": format_local(_now_utc()),
        }
    )
    enabled_pairs = list(db.scalars(select(TradingPair).where(TradingPair.enabled.is_(True)).order_by(TradingPair.symbol.asc())))
    if enabled_pairs:
        events.append(
            {
                "step": "pairs_loaded",
                "status": "ok",
                "message": f"Loaded enabled pairs: {', '.join(pair.symbol for pair in enabled_pairs)}.",
                "timestamp": format_local(_now_utc()),
            }
        )
    latest_rows = list(db.scalars(select(TradeExecution).order_by(TradeExecution.created_at.desc()).limit(limit)))
    for row in reversed(latest_rows):
        status_map = {
            "sent": ("executing_trade", "ok", "Order placed successfully on MT5 demo account."),
            "blocked": ("risk_gate", "warn", "Signal blocked by policy/risk window."),
            "failed": ("execution_error", "error", "Order attempt failed."),
            "skipped": ("skip", "warn", "Signal skipped (cooldown or duplicate prevention)."),
        }
        step, level, base_message = status_map.get(row.status, ("analysis", "info", "Execution update recorded."))
        events.append(
            {
                "step": step,
                "status": level,
                "message": f"{base_message} {row.symbol} {row.timeframe} {row.direction.upper()} · {row.reason}",
                "timestamp": format_local(row.created_at),
                "execution_id": row.execution_id,
            }
        )
    if account and account.trading_mode != "demo_auto":
        events.append(
            {
                "step": "mode",
                "status": "warn",
                "message": "Auto trading is stopped (monitor_only). Start Demo Auto Trade to run new cycles.",
                "timestamp": format_local(_now_utc()),
            }
        )
    return {
        "account_id": account.account_id if account else None,
        "trading_mode": account.trading_mode if account else "monitor_only",
        "guard_enabled": _guard_enabled_for_demo(),
        "items": events[-limit:],
    }


@router.get("/executions")
def list_executions(
    limit: int = Query(default=120, ge=1, le=1000),
    symbol: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = select(TradeExecution)
    if symbol:
        query = query.where(TradeExecution.symbol == symbol.upper())
    if status_filter:
        query = query.where(TradeExecution.status == status_filter)
    rows = list(db.scalars(query.order_by(TradeExecution.created_at.desc()).limit(limit)))
    return {
        "items": [
            {
                "execution_id": row.execution_id,
                "account_id": row.account_id,
                "symbol": row.symbol,
                "timeframe": row.timeframe,
                "strategy_id": row.strategy_id,
                "signal_id": row.signal_id,
                "direction": row.direction,
                "volume": row.volume,
                "status": row.status,
                "reason": row.reason,
                "guard_checks_json": row.guard_checks_json,
                "mt5_check_json": row.mt5_check_json,
                "mt5_send_json": row.mt5_send_json,
                "created_at": iso_local(row.created_at),
            }
            for row in rows
        ]
    }


@router.post("/demo-auto/execute", status_code=status.HTTP_202_ACCEPTED)
def execute_demo_auto_cycle(
    request: Request,
    x_runner_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not _runner_allowed(request, x_runner_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Runner authentication required")
    account = _active_demo_account(db, runtime_value("DEMO_EXECUTION_ACCOUNT_ID", "demo_main"))
    if not account:
        raise HTTPException(status_code=404, detail="No enabled demo account found")
    regenerated_signals = 0
    if runtime_bool("DEMO_EXECUTION_REFRESH_SIGNALS", True):
        regenerated_signals = _refresh_signals_for_enabled_pairs(db)
        db.commit()
    candidates = _eligible_signal_rows(db, runtime_int("DEMO_EXECUTION_SIGNAL_MAX_AGE_MINUTES", 10))
    positions_result = _bridge_request("GET", "/positions")
    positions_payload = positions_result.get("body", {}).get("positions", []) if positions_result.get("ok") else []
    if not isinstance(positions_payload, list):
        positions_payload = []
    records: list[TradeExecution] = []
    for pair, timeframe, signal in candidates[: max(1, runtime_int("DEMO_EXECUTION_MAX_PER_CYCLE", 4))]:
        records.append(_execute_one_signal(db, account, pair, timeframe, signal, positions_payload))
    db.commit()
    sent = sum(1 for row in records if row.status == "sent")
    blocked = sum(1 for row in records if row.status == "blocked")
    failed = sum(1 for row in records if row.status == "failed")
    skipped = sum(1 for row in records if row.status == "skipped")
    audit(
        db,
        None,
        "run",
        "demo_auto_execution_cycle",
        account.account_id,
        {
            "candidates": len(candidates),
            "executed_records": len(records),
            "sent": sent,
            "blocked": blocked,
            "failed": failed,
            "skipped": skipped,
        },
    )
    db.commit()
    return {
        "status": "completed",
        "account_id": account.account_id,
        "trading_mode": account.trading_mode,
        "candidate_signals": len(candidates),
        "signals_regenerated": regenerated_signals,
        "executed_records": len(records),
        "sent": sent,
        "blocked": blocked,
        "failed": failed,
        "skipped": skipped,
        "latest": [
            {
                "execution_id": row.execution_id,
                "symbol": row.symbol,
                "timeframe": row.timeframe,
                "direction": row.direction,
                "status": row.status,
                "reason": row.reason,
                "created_at": iso_local(row.created_at),
            }
            for row in records
        ],
    }


@router.post("/demo-auto/run", status_code=status.HTTP_202_ACCEPTED)
def execute_demo_auto_cycle_admin(
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not has_permission(principal.role, "agents:write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    account = _active_demo_account(db, runtime_value("DEMO_EXECUTION_ACCOUNT_ID", "demo_main"))
    if not account:
        raise HTTPException(status_code=404, detail="No enabled demo account found")
    regenerated_signals = 0
    if runtime_bool("DEMO_EXECUTION_REFRESH_SIGNALS", True):
        regenerated_signals = _refresh_signals_for_enabled_pairs(db)
        db.commit()
    candidates = _eligible_signal_rows(db, runtime_int("DEMO_EXECUTION_SIGNAL_MAX_AGE_MINUTES", 10))
    positions_result = _bridge_request("GET", "/positions")
    positions_payload = positions_result.get("body", {}).get("positions", []) if positions_result.get("ok") else []
    if not isinstance(positions_payload, list):
        positions_payload = []
    records: list[TradeExecution] = []
    for pair, timeframe, signal in candidates[: max(1, runtime_int("DEMO_EXECUTION_MAX_PER_CYCLE", 4))]:
        records.append(_execute_one_signal(db, account, pair, timeframe, signal, positions_payload))
    db.commit()
    sent = sum(1 for row in records if row.status == "sent")
    blocked = sum(1 for row in records if row.status == "blocked")
    failed = sum(1 for row in records if row.status == "failed")
    skipped = sum(1 for row in records if row.status == "skipped")
    audit(
        db,
        principal,
        "run",
        "demo_auto_execution_cycle",
        account.account_id,
        {
            "candidates": len(candidates),
            "executed_records": len(records),
            "sent": sent,
            "blocked": blocked,
            "failed": failed,
            "skipped": skipped,
        },
    )
    db.commit()
    return {
        "status": "completed",
        "account_id": account.account_id,
        "trading_mode": account.trading_mode,
        "candidate_signals": len(candidates),
        "signals_regenerated": regenerated_signals,
        "executed_records": len(records),
        "sent": sent,
        "blocked": blocked,
        "failed": failed,
        "skipped": skipped,
        "latest": [
            {
                "execution_id": row.execution_id,
                "symbol": row.symbol,
                "timeframe": row.timeframe,
                "direction": row.direction,
                "status": row.status,
                "reason": row.reason,
                "created_at": iso_local(row.created_at),
            }
            for row in records
        ],
    }

