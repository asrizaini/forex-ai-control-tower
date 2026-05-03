from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import create_app
from openclaw_gateway.api_bridge import action_allowed, can_execute_trade


def test_openclaw_disabled_and_forbids_trading():
    assert can_execute_trade() is False
    allowed, reason = action_allowed("direct_mt5_execution", approved=True)
    assert allowed is False
    assert reason in {"openclaw_disabled", "forbidden_action"}


def test_openclaw_action_check_api(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    configure_database(f"sqlite:///{tmp_path / 'openclaw.db'}")
    init_db()
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
