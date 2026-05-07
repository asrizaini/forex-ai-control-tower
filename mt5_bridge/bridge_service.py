from __future__ import annotations

import os
import time
import re
from numbers import Integral
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import Response

from execution_guard.approval_token import validate_approval_token
try:
    from .account_profile import AccountProfile, load_account_profiles, profile_for_account, save_account_profiles
    from .multi_terminal_manager import account_route_map
    from .mt5_client import MT5Client, MT5Unavailable
except ImportError:
    from account_profile import AccountProfile, load_account_profiles, profile_for_account, save_account_profiles
    from multi_terminal_manager import account_route_map
    from mt5_client import MT5Client, MT5Unavailable

BRIDGE_MODE = os.getenv("BRIDGE_MODE", "demo")
ALLOW_LIVE_TRADING = os.getenv("ALLOW_LIVE_TRADING", "false").lower() == "true"
REQUIRE_ORDER_CHECK = os.getenv("REQUIRE_ORDER_CHECK", "true").lower() == "true"

checked_orders: dict[str, dict[str, Any]] = {}
app = FastAPI(title="Forex AI MT5 Bridge", version="0.1.0")

MT5_CONNECTED = Gauge("forex_mt5_bridge_connected", "MT5 terminal connection state, 1 for connected")
MT5_PROFILE_COUNT = Gauge("forex_mt5_bridge_profile_count", "Configured MT5 account profile count")
MT5_PROFILE_ENABLED = Gauge("forex_mt5_bridge_profile_enabled", "MT5 account profile enabled state", ["account_id", "environment", "trading_mode"])
MT5_CHECKED_ORDERS = Gauge("forex_mt5_bridge_checked_orders_total", "In-memory checked order count")
MT5_ORDER_CHECKS = Counter("forex_mt5_order_check_total", "MT5 order_check calls", ["account_id", "symbol", "retcode"])
MT5_ORDER_SENDS = Counter("forex_mt5_order_send_total", "MT5 order_send calls", ["account_id", "symbol", "result"])
MT5_ORDER_CHECK_LATENCY = Histogram("forex_mt5_order_check_latency_seconds", "MT5 order_check latency")
MT5_ORDER_SEND_LATENCY = Histogram("forex_mt5_order_send_latency_seconds", "MT5 order_send latency")


class OrderRequest(BaseModel):
    client_order_id: str = Field(default_factory=lambda: f"order-{int(time.time())}")
    account_id: str
    symbol: str
    side: str
    volume: float
    live_order: bool = False
    price: float | None = None
    sl: float | None = None
    tp: float | None = None
    deviation: int = 20


class AccountProfileIn(BaseModel):
    account_id: str = Field(min_length=1, max_length=80)
    terminal_port: int = Field(ge=8501, le=8599)
    environment: str = Field(default="demo", pattern="^(dev|staging|demo|production-live)$")
    trading_mode: str = "monitor_only"
    terminal_path: str | None = None
    enabled: bool = True


def require_bridge_token(x_bridge_token: str | None = Header(default=None)) -> None:
    expected = os.getenv("BRIDGE_API_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="BRIDGE_API_TOKEN is not configured")
    if not x_bridge_token or x_bridge_token != expected:
        raise HTTPException(status_code=401, detail="Bridge API token required")


def client() -> MT5Client:
    try:
        return MT5Client()
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def mt5_request(order: OrderRequest) -> dict[str, Any]:
    mt5 = client().mt5
    order_type = mt5.ORDER_TYPE_BUY if order.side == "BUY" else mt5.ORDER_TYPE_SELL
    # MT5 broker validation is strict on comment length/charset.
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", order.client_order_id)[:20] or f"{int(time.time())}"
    comment = f"fxai_{safe_id}"[:31]
    request: dict[str, Any] = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": order.symbol,
        "volume": order.volume,
        "type": order_type,
        "deviation": order.deviation,
        "magic": 810081,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    symbol_info = mt5.symbol_info(order.symbol)
    if symbol_info is not None:
        filling_mode = getattr(symbol_info, "filling_mode", None)
        if isinstance(filling_mode, Integral):
            request["type_filling"] = int(filling_mode)
    if order.price is not None:
        request["price"] = order.price
    if order.sl is not None:
        request["sl"] = order.sl
    if order.tp is not None:
        request["tp"] = order.tp
    return request


def require_known_account(account_id: str) -> AccountProfile:
    profile = profile_for_account(account_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Unknown MT5 bridge account profile")
    if not profile.enabled:
        raise HTTPException(status_code=403, detail="MT5 bridge account profile is disabled")
    return profile


def order_check_with_fallback(order_request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    mt5 = client().mt5
    candidates: list[int] = []
    for mode in (
        order_request.get("type_filling"),
        getattr(mt5, "ORDER_FILLING_RETURN", None),
        getattr(mt5, "ORDER_FILLING_IOC", None),
        getattr(mt5, "ORDER_FILLING_FOK", None),
    ):
        if isinstance(mode, Integral):
            normalized = int(mode)
            if normalized not in candidates:
                candidates.append(normalized)

    last_result: dict[str, Any] = {"retcode": -1}
    for mode in candidates:
        trial = dict(order_request)
        trial["type_filling"] = mode
        result = client().order_check(trial)
        last_result = result
        # 10030 = unsupported filling mode for this symbol/broker.
        if int(result.get("retcode", -1)) != 10030:
            return trial, result
    return dict(order_request), last_result


def refresh_bridge_metrics(connected: bool | None = None) -> None:
    profiles = load_account_profiles()
    MT5_PROFILE_COUNT.set(len(profiles))
    MT5_CHECKED_ORDERS.set(len(checked_orders))
    if connected is not None:
        MT5_CONNECTED.set(1 if connected else 0)
    for profile in profiles:
        MT5_PROFILE_ENABLED.labels(
            account_id=profile.account_id,
            environment=profile.environment,
            trading_mode=profile.trading_mode,
        ).set(1 if profile.enabled else 0)


@app.get("/health")
def health() -> dict[str, Any]:
    connected = False
    error = None
    try:
        connected = client().connect()
    except HTTPException as exc:
        error = exc.detail
    refresh_bridge_metrics(connected)
    return {
        "status": "ok" if connected else "degraded",
        "bridge_mode": BRIDGE_MODE,
        "allow_live_trading": ALLOW_LIVE_TRADING,
        "require_order_check": REQUIRE_ORDER_CHECK,
        "mt5_connected": connected,
        "mt5_terminal_path_configured": bool(os.getenv("MT5_TERMINAL_PATH")),
        "multi_account_profiles": len(load_account_profiles()),
        "account_routes": account_route_map(),
        "error": error,
    }


@app.get("/metrics", dependencies=[Depends(require_bridge_token)])
def metrics() -> Response:
    refresh_bridge_metrics()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/observability", dependencies=[Depends(require_bridge_token)])
def observability() -> dict[str, Any]:
    refresh_bridge_metrics()
    return {
        "bridge_mode": BRIDGE_MODE,
        "allow_live_trading": ALLOW_LIVE_TRADING,
        "require_order_check": REQUIRE_ORDER_CHECK,
        "checked_orders_count": len(checked_orders),
        "profile_count": len(load_account_profiles()),
        "account_routes": account_route_map(),
        "metrics": [
            "forex_mt5_bridge_connected",
            "forex_mt5_bridge_profile_count",
            "forex_mt5_bridge_profile_enabled",
            "forex_mt5_bridge_checked_orders_total",
            "forex_mt5_order_check_total",
            "forex_mt5_order_send_total",
            "forex_mt5_order_check_latency_seconds",
            "forex_mt5_order_send_latency_seconds",
        ],
    }


@app.get("/account", dependencies=[Depends(require_bridge_token)])
def account() -> dict[str, Any]:
    try:
        return client().account_info()
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/accounts/profiles", dependencies=[Depends(require_bridge_token)])
def account_profiles() -> dict[str, Any]:
    return {"accounts": [profile.__dict__ for profile in load_account_profiles()]}


@app.post("/accounts/profiles", dependencies=[Depends(require_bridge_token)])
def upsert_account_profile(profile: AccountProfileIn) -> dict[str, Any]:
    if profile.environment == "production-live":
        raise HTTPException(status_code=403, detail="production-live profile requires governance workflow")
    profiles = [item for item in load_account_profiles() if item.account_id != profile.account_id]
    profiles.append(AccountProfile(**profile.model_dump()))
    save_account_profiles(profiles)
    return {"saved": True, "account_id": profile.account_id, "terminal_port": profile.terminal_port}


@app.get("/accounts/{account_id}/route", dependencies=[Depends(require_bridge_token)])
def account_route(account_id: str) -> dict[str, Any]:
    profile = require_known_account(account_id)
    return {
        "account_id": profile.account_id,
        "terminal_port": profile.terminal_port,
        "environment": profile.environment,
        "trading_mode": profile.trading_mode,
        "terminal_path_configured": bool(profile.terminal_path),
        "enabled": profile.enabled,
    }


@app.get("/symbols", dependencies=[Depends(require_bridge_token)])
def symbols() -> dict[str, Any]:
    try:
        return {"symbols": client().symbols()}
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/symbols/{symbol}/info", dependencies=[Depends(require_bridge_token)])
def symbol_info(symbol: str) -> dict[str, Any]:
    try:
        return {"symbol": symbol, "info": client().symbol_info(symbol)}
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/rates/{symbol}", dependencies=[Depends(require_bridge_token)])
def rates(symbol: str, timeframe: str = Query(default="M1"), count: int = Query(default=100, ge=10, le=1000)) -> dict[str, Any]:
    try:
        normalized_timeframe = str(timeframe).upper()
        return {"symbol": symbol, "timeframe": normalized_timeframe, "rates": client().rates(symbol, normalized_timeframe, count=count)}
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/ticks/{symbol}", dependencies=[Depends(require_bridge_token)])
def ticks(symbol: str) -> dict[str, Any]:
    try:
        return {"symbol": symbol, "tick": client().ticks(symbol)}
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/order/check", dependencies=[Depends(require_bridge_token)])
def order_check(order: OrderRequest) -> dict[str, Any]:
    require_known_account(order.account_id)
    if order.live_order and not ALLOW_LIVE_TRADING:
        raise HTTPException(status_code=403, detail="Live trading is disabled")
    try:
        started = time.time()
        request_payload = mt5_request(order)
        resolved_request, result = order_check_with_fallback(request_payload)
        MT5_ORDER_CHECK_LATENCY.observe(time.time() - started)
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    checked_orders[order.client_order_id] = {"result": result, "request": resolved_request}
    MT5_CHECKED_ORDERS.set(len(checked_orders))
    MT5_ORDER_CHECKS.labels(account_id=order.account_id, symbol=order.symbol, retcode=str(result.get("retcode", "unknown"))).inc()
    return {"client_order_id": order.client_order_id, "check_passed": result.get("retcode") == 0, "result": result}


@app.post("/order/send", dependencies=[Depends(require_bridge_token)])
def order_send(order: OrderRequest, x_execution_guard_token: str | None = Header(default=None)) -> dict[str, Any]:
    require_known_account(order.account_id)
    if order.live_order and not ALLOW_LIVE_TRADING:
        raise HTTPException(status_code=403, detail="Live trading is disabled")
    checked_entry: dict[str, Any] | None = None
    if REQUIRE_ORDER_CHECK:
        checked_entry = checked_orders.get(order.client_order_id)
    if REQUIRE_ORDER_CHECK and checked_entry is None:
        raise HTTPException(status_code=409, detail="order_check must run before order_send")
    if not validate_approval_token(x_execution_guard_token):
        raise HTTPException(status_code=403, detail="Execution Guard approval token required")
    request_payload = mt5_request(order)
    if checked_entry:
        cached_request = checked_entry.get("request")
        if isinstance(cached_request, dict):
            request_payload = cached_request
    try:
        started = time.time()
        result = client().order_send(request_payload)
        MT5_ORDER_SEND_LATENCY.observe(time.time() - started)
    except MT5Unavailable as exc:
        MT5_ORDER_SENDS.labels(account_id=order.account_id, symbol=order.symbol, result="mt5_unavailable").inc()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    MT5_ORDER_SENDS.labels(account_id=order.account_id, symbol=order.symbol, result=str(result.get("retcode", "sent"))).inc()
    return {"client_order_id": order.client_order_id, "sent": True, "result": result}


@app.get("/positions", dependencies=[Depends(require_bridge_token)])
def positions() -> dict[str, Any]:
    try:
        return {"positions": client().positions()}
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/history", dependencies=[Depends(require_bridge_token)])
def history() -> dict[str, Any]:
    try:
        return {"history": client().history()}
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
