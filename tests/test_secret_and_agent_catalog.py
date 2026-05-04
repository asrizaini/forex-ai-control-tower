from fastapi.testclient import TestClient

from agents.catalog import AGENT_CATALOG
from agents.workflow_engine import seed_agent_catalog
from control.api.auth import issue_token
from control.api.db import SessionLocal, configure_database, init_db
from control.api.main import create_app
from control.api.models import AgentState, AgentToolPolicy, AuditLog


def test_secret_manager_status_does_not_expose_secret_values(monkeypatch, tmp_path):
    monkeypatch.setenv("POSTGRES_PASSWORD", "example-postgres")
    monkeypatch.setenv("GRAFANA_ADMIN_PASSWORD", "example-grafana")
    monkeypatch.setenv("JWT_SECRET_KEY", "example-jwt")
    monkeypatch.setenv("EXECUTION_GUARD_SIGNING_KEY", "example-guard")
    monkeypatch.setenv("BRIDGE_API_TOKEN", "example-bridge")
    configure_database(f"sqlite:///{tmp_path / 'secret_status.db'}")
    init_db()
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


def test_credentials_center_masks_updates_and_audits(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    monkeypatch.setenv("CREDENTIAL_STORE_DEV_KEY_FILE", str(tmp_path / "credential_store.key"))
    configure_database(f"sqlite:///{tmp_path / 'credentials.db'}")
    init_db()
    client = TestClient(create_app())
    token = issue_token("admin", "super_admin")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    generated = client.post("/api/v1/credentials/JWT_SECRET_KEY/generate", headers=headers).json()
    assert generated["value"]
    assert generated["stored"] is False

    response = client.put("/api/v1/credentials/NEWS_PROVIDER_API_KEY", headers=headers, json={"value": "fmp-test-secret"})
    assert response.status_code == 200
    assert "fmp-test-secret" not in str(response.json())

    status = client.get("/api/v1/credentials/status", headers=headers).json()
    news_item = next(item for item in status["items"] if item["name"] == "NEWS_PROVIDER_API_KEY")
    assert news_item["configured"] is True
    assert news_item["masked_value"] != "fmp-test-secret"
    assert "fmp-test-secret" not in str(status)

    reveal = client.post("/api/v1/credentials/NEWS_PROVIDER_API_KEY/reveal", headers=headers, json={"confirm": True}).json()
    assert reveal["value"] == "fmp-test-secret"

    db = SessionLocal()
    try:
        audit_actions = [row.action for row in db.query(AuditLog).filter(AuditLog.resource_id == "NEWS_PROVIDER_API_KEY")]
        assert "credential_update" in audit_actions
        assert "credential_reveal" in audit_actions
        assert "fmp-test-secret" not in str([row.details for row in db.query(AuditLog).all()])
    finally:
        db.close()
