from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import create_app


def test_demo_validation_report_lists_blockers_and_can_pass(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    configure_database(f"sqlite:///{tmp_path / 'demo-report.db'}")
    init_db()
    client = TestClient(create_app())
    headers = {"Authorization": f"Bearer {issue_token('admin', 'super_admin')['access_token']}"}

    empty = client.get("/api/v1/strategies/records/trend_pullback_v1/demo-validation-report").json()
    assert empty["demo_validation_passed"] is False
    assert "missing_completed_backtest" in empty["blockers"]

    client.post(
        "/api/v1/backtests/jobs",
        headers=headers,
        json={"strategy_id": "trend_pullback_v1", "symbol": "EURUSD", "timeframe": "H1"},
    )
    client.post(
        "/api/v1/forward-tests/jobs",
        headers=headers,
        json={"strategy_id": "trend_pullback_v1", "symbol": "EURUSD", "timeframe": "H1"},
    )
    client.post(
        "/api/v1/approvals/requests",
        headers=headers,
        json={
            "user_id": "admin",
            "account_id": "demo_main",
            "strategy_id": "trend_pullback_v1",
            "symbol": "EURUSD",
            "side": "BUY",
            "volume": 0.01,
            "environment": "demo",
        },
    )

    report = client.get("/api/v1/strategies/records/trend_pullback_v1/demo-validation-report").json()
    assert report["backtest_jobs"] == 1
    assert report["forward_test_jobs"] == 1
    assert report["demo_approval_records"] == 1
    assert report["live_trading_allowed"] is False
