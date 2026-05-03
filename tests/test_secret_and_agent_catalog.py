from fastapi.testclient import TestClient

from agents.catalog import AGENT_CATALOG
from agents.workflow_engine import seed_agent_catalog
from control.api.db import SessionLocal, configure_database, init_db
from control.api.main import create_app
from control.api.models import AgentState, AgentToolPolicy


def test_secret_manager_status_does_not_expose_secret_values(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "example-postgres")
    monkeypatch.setenv("GRAFANA_ADMIN_PASSWORD", "example-grafana")
    monkeypatch.setenv("JWT_SECRET_KEY", "example-jwt")
    monkeypatch.setenv("EXECUTION_GUARD_SIGNING_KEY", "example-guard")
    monkeypatch.setenv("BRIDGE_API_TOKEN", "example-bridge")
    client = TestClient(create_app())

    response = client.get("/api/v1/system/secret-manager/status")

    assert response.status_code == 200
    body = response.json()
    assert body["required_runtime_secrets_present"] is True
    assert "example-postgres" not in str(body)
    assert body["required_runtime_secrets"]["POSTGRES_PASSWORD"] is True


def test_agent_catalog_endpoint_and_seed(monkeypatch, tmp_path):
    configure_database(f"sqlite:///{tmp_path / 'catalog.db'}")
    init_db()
    client = TestClient(create_app())

    response = client.get("/api/v1/agents/catalog")
    assert response.status_code == 200
    assert len(response.json()["agents"]) == len(AGENT_CATALOG)

    count = seed_agent_catalog()
    db = SessionLocal()
    try:
        assert count == len(AGENT_CATALOG)
        assert db.query(AgentState).count() == len(AGENT_CATALOG)
        assert db.query(AgentToolPolicy).count() >= len(AGENT_CATALOG)
    finally:
        db.close()

