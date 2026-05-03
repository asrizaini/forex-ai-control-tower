from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import create_app
from notifications.hub import channel_status, route_notification


def test_notification_routing_and_quiet_hours():
    routed = route_notification("warning", quiet_hours_enabled=False, env={"TELEGRAM_BOT_TOKEN": "set", "FCM_SERVER_KEY": "set", "FCM_PROJECT_ID": "set"})
    assert routed["routed_channels"] == ["telegram", "mobile_push"]
    quiet = route_notification("normal", quiet_hours_enabled=True, env={"TELEGRAM_BOT_TOKEN": "set"})
    assert quiet["routed_channels"] == []
    emergency = route_notification("emergency", quiet_hours_enabled=True, env={"TELEGRAM_BOT_TOKEN": "set"})
    assert "dashboard" in emergency["routed_channels"]
    assert channel_status({})["dashboard"]["configured"] is True


def test_notification_event_api(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    configure_database(f"sqlite:///{tmp_path / 'notifications.db'}")
    init_db()
    app = create_app()
    client = TestClient(app)
    token = issue_token("admin", "super_admin")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    status = client.get("/api/v1/notifications/channels/status").json()
    assert status["channels"]["dashboard"]["delivery_enabled"] is True

    event = client.post(
        "/api/v1/notifications/events",
        headers=headers,
        json={"level": "critical", "notification_type": "approval_request", "title": "Demo approval", "message": "Approval required.", "language": "ms-MY"},
    )
    assert event.status_code == 200
    body = event.json()
    assert body["language"] == "ms-MY"
    assert body["status"] in {"queued", "pending_channel_configuration"}

    events = client.get("/api/v1/notifications/events").json()
    assert events[0]["notification_type"] == "approval_request"
