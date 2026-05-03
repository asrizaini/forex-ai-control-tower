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


def test_orchestrator_console_serves_embeddable_ui():
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/agent-theater/console")

    assert response.status_code == 200
    assert "Orchestrator Console" in response.text
    assert "/api/v1/agent-theater/chat" in response.text


def test_agent_theater_modes_and_ms_my_rendering(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    app = create_app()
    client = TestClient(app, client=("10.10.1.84", 12345))

    modes = client.get("/api/v1/agent-theater/modes").json()["modes"]
    assert "Debate Mode" in {mode["name"] for mode in modes}
    assert "System Improvement Room" in {mode["name"] for mode in modes}

    response = client.post(
        "/api/v1/agent-theater/events",
        json={
            "agent": "News Agent",
            "stream": "Live Chat View",
            "summary": "News adapter is not connected yet. Until ForexFactory/economic-calendar integration is live, high-impact news status stays conservative.",
            "risk_status": "news_safe_mode",
            "next_action": "Continue monitoring.",
        },
    )
    assert response.status_code == 202

    rendered = client.get("/api/v1/agent-theater/events?language=ms-MY").json()["events"][0]
    assert rendered["display"]["language"] == "ms-MY"
    assert "Adapter berita" in rendered["display"]["summary"]
    assert rendered["display"]["risk_status"] == "mod_selamat_berita"


def test_orchestrator_chat_supports_debate_and_improvement_rooms(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    configure_database(f"sqlite:///{tmp_path / 'control.db'}")
    init_db()
    app = create_app()
    client = TestClient(app, client=("10.10.1.50", 12345))

    response = client.post(
        "/api/v1/agent-theater/chat",
        json={"message": "Debate the next roadmap improvement step.", "language": "en", "session_id": "test-session"},
    )

    assert response.status_code == 202
    streams = {event["stream"] for event in client.get("/api/v1/agent-theater/events").json()["events"]}
    assert "Debate Mode" in streams
    assert "System Improvement Room" in streams
