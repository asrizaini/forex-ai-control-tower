from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import create_app
from strategies.registry import discover_plugins


def test_strategy_plugin_discovery():
    plugins = discover_plugins()
    ids = {plugin.strategy_id for plugin in plugins}
    assert "trend_pullback_v1" in ids
    plugin = next(plugin for plugin in plugins if plugin.strategy_id == "trend_pullback_v1")
    assert "demo" in plugin.allowed_environments
    assert "production-live" not in plugin.allowed_environments


def test_strategy_plugin_sync_promotion_and_permission(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    configure_database(f"sqlite:///{tmp_path / 'strategy.db'}")
    init_db()
    app = create_app()
    client = TestClient(app)
    token = issue_token("admin", "super_admin")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    plugins = client.get("/api/v1/strategies/plugins").json()["plugins"]
    assert any(plugin["strategy_id"] == "trend_pullback_v1" for plugin in plugins)

    synced = client.post("/api/v1/strategies/plugins/sync", headers=headers)
    assert synced.status_code == 200
    synced_ids = [s["strategy_id"] for s in synced.json()]
    assert "trend_pullback_v1" in synced_ids

    bad_jump = client.post(
        "/api/v1/strategies/records/trend_pullback_v1/promote",
        headers=headers,
        json={"target_state": "approved_for_demo_auto"},
    )
    assert bad_jump.status_code == 400

    promoted = client.post(
        "/api/v1/strategies/records/trend_pullback_v1/promote",
        headers=headers,
        json={"target_state": "backtesting", "notes": "Start controlled backtest gate."},
    )
    assert promoted.status_code == 200
    assert promoted.json()["lifecycle_state"] == "backtesting"

    granted = client.post(
        "/api/v1/strategies/records/trend_pullback_v1/permissions",
        headers=headers,
        json={"user_id": "admin", "account_id": "demo_main"},
    )
    assert granted.status_code == 200
    assert granted.json()["granted"] is True

    approvals = client.get("/api/v1/strategies/records/trend_pullback_v1/approvals").json()
    assert approvals[0]["target_state"] == "backtesting"
