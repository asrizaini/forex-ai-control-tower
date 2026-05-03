from fastapi.testclient import TestClient

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
