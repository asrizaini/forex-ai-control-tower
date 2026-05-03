from fastapi.testclient import TestClient

from control.api.auth import issue_token
from control.api.db import configure_database, init_db
from control.api.main import create_app
from strategies.lab import quality_score


def test_strategy_lab_quality_score_weights():
    score = quality_score(
        drawdown_pct=6.0,
        profit_factor=1.8,
        forward_consistency=0.75,
        win_rate_stability=0.7,
        execution_quality=0.8,
    )
    assert 0 < score.quality_score <= 100
    assert score.drawdown_control == 0.8


def test_strategy_lab_job_endpoints(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-jwt-key")
    configure_database(f"sqlite:///{tmp_path / 'lab.db'}")
    init_db()
    app = create_app()
    client = TestClient(app)
    token = issue_token("admin", "super_admin")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"strategy_id": "trend_pullback_v1", "symbol": "EURUSD", "timeframe": "H1", "parameters_json": {"risk": "demo"}}

    backtest = client.post("/api/v1/backtests/jobs", headers=headers, json=payload)
    assert backtest.status_code == 200
    assert backtest.json()["status"] == "completed_mock"
    assert backtest.json()["quality_score"] is not None

    forward = client.post("/api/v1/forward-tests/jobs", headers=headers, json=payload)
    assert forward.status_code == 200
    assert forward.json()["status"] == "scheduled"

    tuning = client.post("/api/v1/tuning/jobs", headers=headers, json=payload)
    assert tuning.status_code == 200
    assert tuning.json()["status"] == "queued"

    leaderboard = client.get("/api/v1/backtests/leaderboard").json()
    assert leaderboard[0]["strategy_id"] == "trend_pullback_v1"

    schedules = client.get("/api/v1/backtests/schedules").json()["schedules"]
    assert "weekend" in schedules
