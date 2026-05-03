from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import app


def test_control_plane_user_create_and_audit(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    configure_database(f"sqlite:///{tmp_path / 'control-plane.db'}")
    init_db()
    token = issue_token("admin", "super_admin")["access_token"]
    client = TestClient(app)

    response = client.post(
        "/api/v1/users/records",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "roadmap-user", "email": "roadmap-user@example.com", "role": "viewer", "language": "en"},
    )

    assert response.status_code == 200
    audit = client.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {token}"})
    assert audit.status_code == 200


def test_control_plane_blocks_live_account_without_governance(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    configure_database(f"sqlite:///{tmp_path / 'control-plane.db'}")
    init_db()
    token = issue_token("admin", "super_admin")["access_token"]
    client = TestClient(app)

    response = client.post(
        "/api/v1/accounts/records",
        headers={"Authorization": f"Bearer {token}"},
        json={"account_id": "live-blocked", "display_name": "Live Blocked", "environment": "production-live"},
    )

    assert response.status_code == 400
