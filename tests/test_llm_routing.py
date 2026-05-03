from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import create_app
from llm_cost_center.router import choose_provider, redact_prompt


def test_llm_router_redacts_and_falls_back_to_local(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert redact_prompt("api_key abc password xyz") == "[REDACTED] abc [REDACTED] xyz"
    route = choose_provider("risk_review", estimated_cost=10.0, daily_spend=0.0, daily_limit=5.0, paid_requested=True)
    assert route["provider"] == "local"
    assert route["reason"] == "budget_limit_fallback"


def test_llm_route_and_model_evaluation_api(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    configure_database(f"sqlite:///{tmp_path / 'llm.db'}")
    init_db()
    app = create_app()
    client = TestClient(app)
    token = issue_token("admin", "super_admin")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    routed = client.post(
        "/api/v1/llm/route",
        headers=headers,
        json={"task_type": "risk_review", "prompt": "Do not leak token value", "paid_requested": True, "estimated_cost": 0.5},
    )
    assert routed.status_code == 200
    body = routed.json()
    assert body["provider"] == "local"
    assert body["prompt_redacted"] is True

    budget = client.get("/api/v1/llm/budget").json()
    assert budget["daily_limit"] == 5.0

    evaluation = client.post(
        "/api/v1/llm/evaluations",
        headers=headers,
        json={"provider": "local", "model": "llama3.1:8b", "task_type": "risk_review", "score": 82},
    )
    assert evaluation.status_code == 200
    assert evaluation.json()["accepted"] is True
