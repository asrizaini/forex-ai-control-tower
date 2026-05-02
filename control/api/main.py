from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from .auth import decode_token
from .routes import (
    accounts,
    agent_theater,
    approvals,
    auth,
    backtests,
    forward_tests,
    localization,
    mobile,
    news,
    notifications,
    openclaw,
    risk,
    signals,
    strategies,
    system,
    trades,
    tuning,
    users,
)

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Forex AI Control Tower",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://10.10.1.81:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in [
        auth.router,
        users.router,
        accounts.router,
        strategies.router,
        signals.router,
        trades.router,
        approvals.router,
        risk.router,
        news.router,
        backtests.router,
        forward_tests.router,
        tuning.router,
        notifications.router,
        agent_theater.router,
        system.router,
        openclaw.router,
        localization.router,
        mobile.router,
    ]:
        app.include_router(router, prefix=API_PREFIX)

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {
            "status": "ok",
            "environment": "demo",
            "trading_mode": "monitor_only",
            "live_auto_trading": False,
        }

    @app.get("/metrics", tags=["system"])
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    async def authenticated_ws(websocket: WebSocket, stream: str) -> None:
        token = websocket.query_params.get("token")
        if not token or not decode_token(token):
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        await websocket.accept()
        await websocket.send_json({"stream": stream, "status": "connected"})
        await websocket.close()

    @app.websocket("/ws/v1/system")
    async def ws_system(websocket: WebSocket) -> None:
        await authenticated_ws(websocket, "system")

    @app.websocket("/ws/v1/signals")
    async def ws_signals(websocket: WebSocket) -> None:
        await authenticated_ws(websocket, "signals")

    @app.websocket("/ws/v1/trades")
    async def ws_trades(websocket: WebSocket) -> None:
        await authenticated_ws(websocket, "trades")

    @app.websocket("/ws/v1/approvals")
    async def ws_approvals(websocket: WebSocket) -> None:
        await authenticated_ws(websocket, "approvals")

    @app.websocket("/ws/v1/risk")
    async def ws_risk(websocket: WebSocket) -> None:
        await authenticated_ws(websocket, "risk")

    @app.websocket("/ws/v1/agent-theater")
    async def ws_agent_theater(websocket: WebSocket) -> None:
        await authenticated_ws(websocket, "agent-theater")

    @app.websocket("/ws/v1/accounts/{account_id}")
    async def ws_account(websocket: WebSocket, account_id: str) -> None:
        await authenticated_ws(websocket, f"accounts/{account_id}")

    @app.websocket("/ws/v1/users/{user_id}")
    async def ws_user(websocket: WebSocket, user_id: str) -> None:
        await authenticated_ws(websocket, f"users/{user_id}")

    return app


app = create_app()
