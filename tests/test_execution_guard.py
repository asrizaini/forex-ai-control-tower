from execution_guard.guard import approve_execution
from execution_guard.approval_token import validate_approval_token
from execution_guard.control_plane import ExecutionTelemetry, evaluate_control_plane_policy
from execution_guard.schemas import ExecutionRequest
from control.api.auth import issue_token
from control.api.db import SessionLocal, configure_database, init_db
from control.api.main import create_app
from control.api.models import Account, PermissionAssignment, RiskPolicy, Strategy, User
from fastapi.testclient import TestClient


def test_monitor_only_blocks_execution_by_default():
    decision = approve_execution(ExecutionRequest(account_id="a1", strategy_id="s1", symbol="EURUSD", side="BUY", volume=0.1))
    assert not decision.approved
    assert any("monitor_only" in reason for reason in decision.reasons)


def test_approval_token_validation_fails_without_signing_key(monkeypatch):
    monkeypatch.delenv("EXECUTION_GUARD_SIGNING_KEY", raising=False)
    assert validate_approval_token("token") is False


def _seed_guard_fixture(tmp_path):
    configure_database(f"sqlite:///{tmp_path / 'guard.db'}")
    init_db()
    db = SessionLocal()
    db.add_all(
        [
            User(user_id="admin", email="admin@example.test", role="super_admin", enabled=True, onboarding_complete=True),
            Account(account_id="demo_main", display_name="Demo Main", environment="demo", trading_mode="demo_auto", enabled=True),
            Strategy(
                strategy_id="trend_pullback_v1",
                name="Trend Pullback v1",
                lifecycle_state="approved_for_demo_auto",
                allowed_environments=["demo"],
            ),
            PermissionAssignment(user_id="admin", permission="trades:execute:demo", enabled=True),
            PermissionAssignment(user_id="admin", account_id="demo_main", permission="account:trade", enabled=True),
            PermissionAssignment(user_id="admin", strategy_id="trend_pullback_v1", permission="strategy:use", enabled=True),
            RiskPolicy(
                scope="account",
                account_id="demo_main",
                max_daily_loss_pct=5.0,
                max_weekly_loss_pct=10.0,
                max_open_trades=3,
                max_trades_per_day=10,
                max_spread_points=25.0,
                metadata_json={"max_slippage_points": 3.0},
            ),
        ]
    )
    db.commit()
    return db


def test_control_plane_guard_allows_only_when_permissions_and_limits_pass(monkeypatch, tmp_path):
    monkeypatch.setenv("EXECUTION_GUARD_SIGNING_KEY", "unit-test-signing-key")
    db = _seed_guard_fixture(tmp_path)
    try:
        request = ExecutionRequest(
            user_id="admin",
            account_id="demo_main",
            strategy_id="trend_pullback_v1",
            symbol="EURUSD",
            side="BUY",
            volume=0.1,
            environment="demo",
            trading_mode="demo_auto",
            order_check_passed=True,
        )
        telemetry = ExecutionTelemetry(
            daily_loss_pct=1.0,
            weekly_loss_pct=2.0,
            open_trades=1,
            trades_today=2,
            spread_points=12.0,
            slippage_points=1.0,
            market_data_quality_ok=True,
            broker_compatibility_ok=True,
            margin_available=True,
            duplicate_trade_risk=False,
            correlation_exposure_ok=True,
            news_halt_active=False,
        )
        policy = evaluate_control_plane_policy(db, request, telemetry)
        assert all(policy.checks.values())
        decision = approve_execution(ExecutionRequest(**{**request.__dict__, "checks": policy.checks}))
        assert decision.approved
        assert decision.token
    finally:
        db.close()


def test_control_plane_guard_blocks_missing_strategy_permission_and_risk_limit(tmp_path):
    db = _seed_guard_fixture(tmp_path)
    try:
        request = ExecutionRequest(
            user_id="admin",
            account_id="demo_main",
            strategy_id="trend_pullback_v1",
            symbol="EURUSD",
            side="BUY",
            volume=0.1,
            environment="demo",
            trading_mode="demo_auto",
        )
        db.query(PermissionAssignment).filter(PermissionAssignment.strategy_id == "trend_pullback_v1").delete()
        db.commit()
        policy = evaluate_control_plane_policy(
            db,
            request,
            ExecutionTelemetry(
                daily_loss_pct=5.0,
                weekly_loss_pct=2.0,
                open_trades=1,
                trades_today=2,
                spread_points=12.0,
                slippage_points=1.0,
                market_data_quality_ok=True,
                broker_compatibility_ok=True,
                margin_available=True,
                duplicate_trade_risk=False,
                correlation_exposure_ok=True,
                news_halt_active=False,
            ),
        )
        assert not policy.checks["strategy_permission"]
        assert not policy.checks["risk_limits"]
        assert "max_daily_loss_reached" in policy.reasons
    finally:
        db.close()


def test_execution_guard_check_endpoint_returns_no_secret_token(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    monkeypatch.setenv("EXECUTION_GUARD_SIGNING_KEY", "unit-test-signing-key")
    db = _seed_guard_fixture(tmp_path)
    db.close()
    app = create_app()
    client = TestClient(app)
    token = issue_token("admin", "super_admin")["access_token"]

    response = client.post(
        "/api/v1/risk/execution/check",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "account_id": "demo_main",
            "strategy_id": "trend_pullback_v1",
            "symbol": "EURUSD",
            "side": "BUY",
            "volume": 0.1,
            "environment": "demo",
            "trading_mode": "demo_auto",
            "order_check_passed": True,
            "daily_loss_pct": 1.0,
            "weekly_loss_pct": 2.0,
            "open_trades": 1,
            "trades_today": 2,
            "spread_points": 12.0,
            "slippage_points": 1.0,
            "market_data_quality_ok": True,
            "broker_compatibility_ok": True,
            "margin_available": True,
            "duplicate_trade_risk": False,
            "correlation_exposure_ok": True,
            "news_halt_active": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["approved"] is True
    assert body["token_issued"] is True
    assert "token" not in body
