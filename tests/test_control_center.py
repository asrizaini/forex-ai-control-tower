from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import create_app


def test_control_center_sources_workers_and_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Kuala_Lumpur")
    configure_database(f"sqlite:///{tmp_path / 'control_center.db'}")
    init_db()
    client = TestClient(create_app())

    status = client.get("/api/v1/api/status")
    assert status.status_code == 200
    assert status.json()["services"]["database"]["status"] == "ok"

    sources = client.get("/api/v1/data-sources")
    assert sources.status_code == 200
    assert any(item["provider"] == "forex_factory" for item in sources.json()["items"])

    workers = client.get("/api/v1/workers/status")
    assert workers.status_code == 200
    assert any(item["worker_id"] == "calendar_worker" for item in workers.json()["workers"])

    settings = client.get("/api/v1/config/status")
    assert settings.status_code == 200
    assert any(item["setting_key"] == "global_timezone" for item in settings.json()["settings"])
    assert any(item["setting_value"] == "Asia/Kuala_Lumpur" for item in settings.json()["settings"])

    worker_time = workers.json()["workers"][0]["next_run_at"]
    assert worker_time.endswith("+08:00")


def test_notification_worker_runs_when_telegram_is_configured(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_telegram_bot_token_12345")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123456789")
    configure_database(f"sqlite:///{tmp_path / 'control_center_notifications.db'}")
    init_db()
    client = TestClient(create_app())

    workers = client.get("/api/v1/workers/status")
    assert workers.status_code == 200
    notification = next(item for item in workers.json()["workers"] if item["worker_id"] == "notification_worker")
    assert notification["status"] == "running"
    assert notification["health_json"]["telegram_ready"] is True


def test_control_center_writes_are_admin_and_audited(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    configure_database(f"sqlite:///{tmp_path / 'control_center_write.db'}")
    init_db()
    client = TestClient(create_app())
    viewer = issue_token("viewer", "viewer")["access_token"]
    admin = issue_token("admin", "super_admin")["access_token"]

    denied = client.post("/api/v1/workers/calendar_worker/restart", headers={"Authorization": f"Bearer {viewer}"})
    assert denied.status_code == 403

    queued = client.post("/api/v1/workers/calendar_worker/restart", headers={"Authorization": f"Bearer {admin}"})
    assert queued.status_code == 200
    assert queued.json()["action"] == "restart"

    logs = client.get("/api/v1/logs/audit?keyword=worker_restart")
    assert logs.status_code == 200
    assert logs.json()["items"][0]["action"] == "worker_restart_requested"
