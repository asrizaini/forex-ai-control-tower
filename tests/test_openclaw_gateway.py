from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from openclaw_gateway.api_bridge import action_allowed, can_execute_trade


def test_openclaw_disabled_and_forbids_trading():
    assert can_execute_trade() is False
    allowed, reason = action_allowed("direct_mt5_execution", approved=True)
    assert allowed is False
    assert reason in {"openclaw_disabled", "forbidden_action"}


def test_openclaw_action_check_api(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    monkeypatch.setenv("OPENCLAW_ENABLED", "false")
    configure_database(f"sqlite:///{tmp_path / 'openclaw.db'}")
    init_db()
    from control.api.main import create_app

    app = create_app()
    client = TestClient(app)
    token = issue_token("admin", "super_admin")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    status = client.get("/api/v1/openclaw").json()
    assert status["enabled"] is False
    assert status["can_execute_trade"] is False

    checked = client.post("/api/v1/openclaw/actions/check", headers=headers, json={"action": "direct_mt5_execution", "approved": True})
    assert checked.status_code == 200
    assert checked.json()["allowed"] is False
    assert checked.json()["trade_execution_allowed"] is False


def test_openclaw_status_query_and_daily_summary(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    monkeypatch.setenv("OPENCLAW_ENABLED", "true")
    configure_database(f"sqlite:///{tmp_path / 'openclaw_enabled.db'}")
    init_db()
    from control.api.main import create_app

    app = create_app()
    client = TestClient(app)
    token = issue_token("admin", "super_admin")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    status = client.get("/api/v1/openclaw/status")
    assert status.status_code == 200
    assert status.json()["enabled"] is True
    assert status.json()["can_execute_trade"] is False

    summary = client.post("/api/v1/openclaw/summary/daily", headers=headers, json={"language": "en"})
    assert summary.status_code == 200
    assert "Daily summary" in summary.json()["summary"]

    query = client.post("/api/v1/openclaw/status/query", headers=headers, json={"target": "workers", "language": "ms-MY"})
    assert query.status_code == 200
    assert query.json()["target"] == "workers"


def test_openclaw_approved_api_call_is_whitelisted(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    monkeypatch.setenv("OPENCLAW_ENABLED", "true")
    configure_database(f"sqlite:///{tmp_path / 'openclaw_whitelist.db'}")
    init_db()
    from control.api.main import create_app

    app = create_app()
    client = TestClient(app)
    admin = issue_token("admin", "super_admin")["access_token"]
    viewer = issue_token("viewer", "viewer")["access_token"]

    denied = client.post(
        "/api/v1/openclaw/api-call",
        headers={"Authorization": f"Bearer {viewer}"},
        json={"path": "/api/v1/system/runtime", "approved": True, "reason": "test"},
    )
    assert denied.status_code == 403

    bad_path = client.post(
        "/api/v1/openclaw/api-call",
        headers={"Authorization": f"Bearer {admin}"},
        json={"path": "/api/v1/trades", "approved": True, "reason": "test"},
    )
    assert bad_path.status_code == 400

    allowed = client.post(
        "/api/v1/openclaw/api-call",
        headers={"Authorization": f"Bearer {admin}"},
        json={"path": "/api/v1/system/runtime", "approved": True, "reason": "ops check"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["allowed"] is True
