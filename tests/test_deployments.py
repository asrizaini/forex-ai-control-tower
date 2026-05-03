from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import create_app


def test_deployment_records_require_admin_and_persist_rollback_plan(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    configure_database(f"sqlite:///{tmp_path / 'deployments.db'}")
    init_db()
    client = TestClient(create_app())
    admin_headers = {"Authorization": f"Bearer {issue_token('admin', 'super_admin')['access_token']}"}
    viewer_headers = {"Authorization": f"Bearer {issue_token('viewer', 'viewer')['access_token']}"}
    payload = {
        "version": "0.2.0",
        "environment": "staging",
        "changelog": "Add backup schedule and observability metrics.",
        "backup_point": "/opt/forex-ai-control-tower/backups/manifests/latest.jsonl",
        "test_result": "passed",
        "approver": "admin",
        "rollback_command": "git checkout previous && ansible-playbook rollback.yml",
        "rollback_target": "0.1.0",
    }

    denied = client.post("/api/v1/deployments/records", headers=viewer_headers, json=payload)
    assert denied.status_code == 403

    created = client.post("/api/v1/deployments/records", headers=admin_headers, json=payload)
    assert created.status_code == 200
    deployment_id = created.json()["deployment_id"]

    plan = client.get(f"/api/v1/deployments/records/{deployment_id}/rollback").json()
    assert plan["rollback_available"] is True
    assert plan["backup_point"] == payload["backup_point"]

    updated = client.post(
        f"/api/v1/deployments/records/{deployment_id}/status",
        headers=admin_headers,
        json={"status": "deployed", "test_result": "passed"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "deployed"


def test_production_live_deployment_requires_passed_tests(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    configure_database(f"sqlite:///{tmp_path / 'deployments-live.db'}")
    init_db()
    client = TestClient(create_app())
    headers = {"Authorization": f"Bearer {issue_token('admin', 'super_admin')['access_token']}"}

    response = client.post(
        "/api/v1/deployments/records",
        headers=headers,
        json={
            "version": "1.0.0",
            "environment": "production-live",
            "changelog": "Live deployment request.",
            "backup_point": "/opt/forex-ai-control-tower/backups/manifests/latest.jsonl",
            "test_result": "failed",
            "approver": "admin",
            "rollback_command": "rollback production-live",
        },
    )

    assert response.status_code == 400
