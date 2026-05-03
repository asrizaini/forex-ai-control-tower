from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import create_app


def test_manual_approval_request_and_decision_are_persisted(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    configure_database(f"sqlite:///{tmp_path / 'approvals.db'}")
    init_db()
    client = TestClient(create_app())
    admin = {"Authorization": f"Bearer {issue_token('admin', 'super_admin')['access_token']}"}
    user = {"Authorization": f"Bearer {issue_token('alice', 'extended_user')['access_token']}"}

    created = client.post(
        "/api/v1/approvals/requests",
        headers=admin,
        json={
            "user_id": "alice",
            "account_id": "demo_main",
            "strategy_id": "trend_pullback_v1",
            "symbol": "EURUSD",
            "side": "BUY",
            "volume": 0.01,
            "environment": "demo",
            "trading_mode": "manual_live",
            "reason": "Manual approval workflow test.",
            "guard_check_json": {"approved": False, "reasons": ["monitor_only"]},
        },
    )
    assert created.status_code == 200
    approval_id = created.json()["approval_id"]

    summary = client.get("/api/v1/mobile/summary", headers=user)
    assert summary.status_code == 200
    assert summary.json()["pending_approvals"][0]["approval_id"] == approval_id

    decided = client.post(
        f"/api/v1/approvals/requests/{approval_id}/decision",
        headers=user,
        json={"decision": "approved", "reason": "Approved for demo-only validation."},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    assert decided.json()["decided_by"] == "alice"


def test_production_live_approval_request_is_blocked(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    configure_database(f"sqlite:///{tmp_path / 'approvals-live.db'}")
    init_db()
    client = TestClient(create_app())
    admin = {"Authorization": f"Bearer {issue_token('admin', 'super_admin')['access_token']}"}

    response = client.post(
        "/api/v1/approvals/requests",
        headers=admin,
        json={
            "user_id": "alice",
            "account_id": "live_main",
            "strategy_id": "trend_pullback_v1",
            "symbol": "EURUSD",
            "side": "BUY",
            "volume": 0.01,
            "environment": "production-live",
        },
    )

    assert response.status_code == 400
