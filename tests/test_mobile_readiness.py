from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import create_app


def test_mobile_bootstrap_exposes_safe_feature_contract(tmp_path):
    configure_database(f"sqlite:///{tmp_path / 'mobile-bootstrap.db'}")
    init_db()
    client = TestClient(create_app())

    response = client.get("/api/v1/mobile/bootstrap")

    assert response.status_code == 200
    body = response.json()
    assert body["environment"] == "demo"
    assert body["live_auto_trading"] is False
    assert body["features"]["push_registration"] is True
    assert body["features"]["push_delivery"] == "pending_fcm_credentials"


def test_mobile_push_registration_requires_auth_and_does_not_return_raw_token(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    configure_database(f"sqlite:///{tmp_path / 'mobile-push.db'}")
    init_db()
    client = TestClient(create_app())
    token = issue_token("admin", "super_admin")["access_token"]
    payload = {
        "provider": "fcm",
        "platform": "android",
        "device_id": "android-test-device",
        "push_token": "fcm-token-placeholder-long-enough",
        "language": "en",
        "preferences_json": {"critical": True},
    }

    denied = client.post("/api/v1/mobile/push/register", json=payload)
    assert denied.status_code in {401, 403}

    registered = client.post("/api/v1/mobile/push/register", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert registered.status_code == 200
    body = registered.json()
    assert body["provider"] == "fcm"
    assert "push_token" not in body
    assert "token_hash" not in body

    listed = client.get("/api/v1/mobile/push/registrations", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    assert listed.json()[0]["device_id"] == "android-test-device"
