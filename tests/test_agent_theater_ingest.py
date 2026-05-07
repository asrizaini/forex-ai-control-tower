from fastapi.testclient import TestClient

from control.api.db import configure_database, init_db
from control.api.main import create_app
from control.api.routes import agent_theater as agent_theater_route


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


def test_orchestrator_chat_reports_kuala_lumpur_time(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Kuala_Lumpur")
    configure_database(f"sqlite:///{tmp_path / 'control_time.db'}")
    init_db()
    app = create_app()
    client = TestClient(app, client=("10.10.1.50", 12345))

    response = client.post(
        "/api/v1/agent-theater/chat",
        json={"message": "What is the current time and date?", "language": "en", "session_id": "time-session"},
    )

    assert response.status_code == 202
    assert "GMT+8" in response.json()["reply"]
    events = client.get("/api/v1/agent-theater/events").json()["events"]
    assert all("GMT+8" in event["timestamp"] for event in events)


def test_agent_theater_converts_legacy_z_timestamps_and_filters_agents(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    event_log.write_text(
        '{"agent":"Orchestrator Agent","stream":"Boardroom Mode","summary":"Legacy","timestamp":"2026-05-04T15:46:22Z"}\n'
        '{"agent":"Risk Manager","stream":"Boardroom Mode","summary":"Risk","timestamp":"2026-05-04T15:47:22Z"}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/agent-theater/events?stream=Boardroom%20Mode&agent=Orchestrator%20Agent")

    assert response.status_code == 200
    body = response.json()
    assert body["agents"] == ["Orchestrator Agent", "Risk Manager"]
    assert len(body["events"]) == 1
    assert body["events"][0]["agent"] == "Orchestrator Agent"
    assert body["events"][0]["timestamp"] == "2026-05-04 11:46:22 PM GMT+8"


def test_orchestrator_only_chat_does_not_publish_supporting_agent_events(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    configure_database(f"sqlite:///{tmp_path / 'control_orchestrator_only.db'}")
    init_db()
    app = create_app()
    client = TestClient(app, client=("10.10.1.50", 12345))

    response = client.post(
        "/api/v1/agent-theater/chat",
        json={
            "message": "Debate the next roadmap improvement step.",
            "language": "en",
            "session_id": "console-only",
            "orchestrator_only": True,
        },
    )

    assert response.status_code == 202
    events = client.get("/api/v1/agent-theater/events?stream=Orchestrator%20Console").json()["events"]
    assert [event["agent"] for event in events] == ["Operator", "Orchestrator Agent"]
    assert {event["stream"] for event in events} == {"Orchestrator Console"}


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


def test_room_seed_creates_multi_agent_transcripts(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    app = create_app()
    client = TestClient(app, client=("10.10.1.50", 12345))

    for room in ("Workflow Timeline", "Boardroom Mode", "Strategy War Room", "Account Routing Room"):
        response = client.post(f"/api/v1/agent-theater/rooms/{room}/seed")
        assert response.status_code == 202
        body = response.json()
        assert len(body["events"]) >= 3
        assert {event["stream"] for event in body["events"]} == {room}

    events = client.get("/api/v1/agent-theater/events?limit=30").json()["events"]
    agents = {event["agent"] for event in events}
    assert "Journal Agent" in agents
    assert "Security Review Agent" in agents
    assert "Backtest Agent" in agents
    assert "Account Router Agent" in agents


def test_orchestrator_local_llm_success(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    monkeypatch.setenv("ORCHESTRATOR_GENERAL_CHAT_MODE", "local")
    monkeypatch.setattr(agent_theater_route, "_ask_local_llm", lambda message, language: "Local LLM success reply.")
    configure_database(f"sqlite:///{tmp_path / 'control_local_success.db'}")
    init_db()
    app = create_app()
    client = TestClient(app, client=("10.10.1.50", 12345))
    response = client.post("/api/v1/agent-theater/chat", json={"message": "general question", "language": "en", "session_id": "local-ok"})
    assert response.status_code == 202
    body = response.json()
    assert body["provider"] == "local"
    assert body["reply"] == "Local LLM success reply."


def test_orchestrator_local_failure_returns_clear_error(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    monkeypatch.setenv("ORCHESTRATOR_GENERAL_CHAT_MODE", "local")
    monkeypatch.setattr(agent_theater_route, "_ask_local_llm", lambda message, language: None)
    configure_database(f"sqlite:///{tmp_path / 'control_local_fail.db'}")
    init_db()
    app = create_app()
    client = TestClient(app, client=("10.10.1.50", 12345))
    response = client.post("/api/v1/agent-theater/chat", json={"message": "general question", "language": "en", "session_id": "providers-fail"})
    assert response.status_code == 503
    assert "Local LLM" in response.json()["detail"] or "unavailable" in response.json()["detail"]


def test_orchestrator_local_only_mode(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    monkeypatch.setenv("ORCHESTRATOR_GENERAL_CHAT_MODE", "local")
    monkeypatch.setattr(agent_theater_route, "_ask_local_llm", lambda message, language: "Local mode response.")
    configure_database(f"sqlite:///{tmp_path / 'control_local_only.db'}")
    init_db()
    app = create_app()
    client = TestClient(app, client=("10.10.1.50", 12345))
    response = client.post("/api/v1/agent-theater/chat", json={"message": "general question", "language": "en", "session_id": "local-only"})
    assert response.status_code == 202
    assert response.json()["provider"] == "local"
    assert response.json()["reply"] == "Local mode response."


def test_orchestrator_disabled_mode(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    monkeypatch.setenv("ORCHESTRATOR_GENERAL_CHAT_MODE", "disabled")
    configure_database(f"sqlite:///{tmp_path / 'control_disabled_mode.db'}")
    init_db()
    app = create_app()
    client = TestClient(app, client=("10.10.1.50", 12345))
    response = client.post("/api/v1/agent-theater/chat", json={"message": "general question", "language": "en", "session_id": "disabled"})
    assert response.status_code == 202
    body = response.json()
    assert body["provider"] == "disabled"
    assert "disabled" in body["reply"].lower()


def test_orchestrator_health_does_not_expose_secrets(monkeypatch, tmp_path):
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("AGENT_THEATER_EVENT_LOG", str(event_log))
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/agent-theater/orchestrator/health")
    assert response.status_code == 200
    payload = response.json()
    assert "local" in payload["provider"]["providers"]
    serialized = str(payload)
    assert "super-secret-key" not in serialized
    assert "password" not in serialized.lower()
