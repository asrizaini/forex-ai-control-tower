from fastapi.testclient import TestClient

from control.api.db import configure_database, init_db
from control.api.main import create_app


def test_agent_theater_ingest_redacts_nested_secrets(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    app = create_app()
    client = TestClient(app, client=("10.10.1.84", 12345))

    response = client.post(
        "/api/v1/agent-theater/events",
        json={
            "agent": "Market Data Agent",
            "summary": "Heartbeat",
            "metadata": {"nested": {"api_key": "do-not-store"}},
        },
    )

    assert response.status_code == 202
    body = client.get("/api/v1/agent-theater/events").json()
    assert body["events"][0]["metadata"]["nested"]["api_key"] == "[REDACTED]"
    assert body["events"][0]["contains_hidden_chain_of_thought"] is False


def test_orchestrator_chat_publishes_safe_reply(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    configure_database(f"sqlite:///{tmp_path / 'control.db'}")
    init_db()
    app = create_app()
    client = TestClient(app, client=("10.10.1.50", 12345))

    response = client.post(
        "/api/v1/agent-theater/chat",
        json={"message": "System status?", "language": "en", "session_id": "test-session"},
    )

    assert response.status_code == 202
    assert "monitor-only" in response.json()["reply"]
    body = client.get("/api/v1/agent-theater/events").json()
    assert [event["agent"] for event in body["events"]] == ["Operator", "Orchestrator Agent"]
    assert body["events"][1]["risk_status"] == "read_only_no_trade_execution"


def test_orchestrator_chat_redacts_secret_like_text(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    configure_database(f"sqlite:///{tmp_path / 'control.db'}")
    init_db()
    app = create_app()
    client = TestClient(app, client=("10.10.1.50", 12345))

    response = client.post(
        "/api/v1/agent-theater/chat",
        json={"message": "my password is example", "language": "en", "session_id": "test-session"},
    )

    assert response.status_code == 202
    body = client.get("/api/v1/agent-theater/events").json()
    assert body["events"][0]["summary"] == "[REDACTED: operator message may contain sensitive text]"
