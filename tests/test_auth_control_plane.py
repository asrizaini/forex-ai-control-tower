from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import create_app
from control.api.security import _totp_code


def test_bootstrap_login_refresh_and_2fa(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("LOCAL_AUTH_BOOTSTRAP_ENABLED", "true")
    monkeypatch.setenv("LOCAL_ADMIN_BOOTSTRAP_PASSWORD", "bootstrap-password-123")
    configure_database(f"sqlite:///{tmp_path / 'auth.db'}")
    init_db()
    client = TestClient(create_app())

    bootstrap = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"user_id": "admin", "email": "admin@example.com", "password": "bootstrap-password-123"},
    )
    assert bootstrap.status_code == 200

    login = client.post("/api/v1/auth/login", json={"user_id": "admin", "password": "bootstrap-password-123"})
    assert login.status_code == 200
    access_token = login.json()["access_token"]
    refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200

    setup = client.post("/api/v1/auth/2fa/setup", headers={"Authorization": f"Bearer {access_token}"})
    assert setup.status_code == 200
    code = _totp_code(setup.json()["secret"], int(__import__("time").time() // 30))
    enabled = client.post("/api/v1/auth/2fa/enable", headers={"Authorization": f"Bearer {access_token}"}, json={"code": code})
    assert enabled.status_code == 200


def test_service_keys_and_agent_tasks_are_admin_only(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    configure_database(f"sqlite:///{tmp_path / 'control.db'}")
    init_db()
    admin_token = issue_token("admin", "super_admin")["access_token"]
    viewer_token = issue_token("viewer", "viewer")["access_token"]
    client = TestClient(create_app())

    denied = client.post(
        "/api/v1/service-keys",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"name": "worker", "permissions": ["telemetry:write"]},
    )
    assert denied.status_code == 403

    created_key = client.post(
        "/api/v1/service-keys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "worker", "permissions": ["telemetry:write"]},
    )
    assert created_key.status_code == 200
    assert created_key.json()["api_key"].startswith(created_key.json()["key_id"])

    created_task = client.post(
        "/api/v1/agents/tasks",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"assigned_agent": "Strategy Agent", "task_type": "strategy_review", "request_json": {"strategy_id": "demo"}},
    )
    assert created_task.status_code == 200
    assert created_task.json()["status"] == "queued"

