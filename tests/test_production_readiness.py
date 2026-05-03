from fastapi.testclient import TestClient

from control.api.db import configure_database, init_db
from control.api.main import create_app


def test_production_readiness_blocks_live_trading_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("POSTGRES_PASSWORD", "x")
    monkeypatch.setenv("GRAFANA_ADMIN_PASSWORD", "x")
    monkeypatch.setenv("JWT_SECRET_KEY", "x")
    monkeypatch.setenv("EXECUTION_GUARD_SIGNING_KEY", "x")
    monkeypatch.setenv("BRIDGE_API_TOKEN", "x")
    configure_database(f"sqlite:///{tmp_path / 'readiness.db'}")
    init_db()
    client = TestClient(create_app())

    response = client.get("/api/v1/system/production-readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["live_trading_allowed"] is False
    assert body["restricted_live_auto_allowed"] is False
    assert "production_live_explicitly_approved" in body["blocking_gates"]
