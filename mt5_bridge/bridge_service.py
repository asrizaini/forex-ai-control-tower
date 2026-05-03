from __future__ import annotations

import os
import time
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
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
    request: dict[str, Any] = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": order.symbol,
        "volume": order.volume,
        "type": order_type,
        "deviation": order.deviation,
        "magic": 810081,
        "comment": f"forex-ai:{order.client_order_id}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
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


@app.get("/health")
def health() -> dict[str, Any]:
    connected = False
    error = None
    try:
        connected = client().connect()
    except HTTPException as exc:
        error = exc.detail
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
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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


@app.get("/rates/{symbol}", dependencies=[Depends(require_bridge_token)])
def rates(symbol: str) -> dict[str, Any]:
    try:
        return {"symbol": symbol, "timeframe": "M1", "rates": client().rates(symbol)}
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
        result = client().order_check(mt5_request(order))
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    checked_orders[order.client_order_id] = result
    return {"client_order_id": order.client_order_id, "check_passed": result.get("retcode") == 0, "result": result}


@app.post("/order/send", dependencies=[Depends(require_bridge_token)])
def order_send(order: OrderRequest, x_execution_guard_token: str | None = Header(default=None)) -> dict[str, Any]:
    require_known_account(order.account_id)
    if order.live_order and not ALLOW_LIVE_TRADING:
        raise HTTPException(status_code=403, detail="Live trading is disabled")
    if REQUIRE_ORDER_CHECK and order.client_order_id not in checked_orders:
        raise HTTPException(status_code=409, detail="order_check must run before order_send")
    if not validate_approval_token(x_execution_guard_token):
        raise HTTPException(status_code=403, detail="Execution Guard approval token required")
    try:
        result = client().order_send(mt5_request(order))
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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
