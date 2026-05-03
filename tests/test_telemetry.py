from fastapi.testclient import TestClient

from control.api.db import configure_database, init_db
from control.api.main import create_app


def test_worker_telemetry_persists_market_snapshot(monkeypatch, tmp_path):
    monkeypatch.delenv("TELEMETRY_INGEST_TOKEN", raising=False)
    configure_database(f"sqlite:///{tmp_path / 'telemetry.db'}")
    init_db()
    client = TestClient(create_app(), client=("10.10.1.84", 12345))

    response = client.post(
        "/api/v1/telemetry/worker-snapshot",
        json={
            "worker": "market",
            "result": {
                "data_quality": "fresh",
                "snapshots": [
                    {
                        "symbol": "EURUSD",
                        "trend": "bullish",
                        "spread": 0.0002,
                        "freshness_seconds": 4,
                        "rates_count": 100,
                        "feed_fresh": True,
                    }
                ],
            },
        },
    )

    assert response.status_code == 202
    assert response.json()["market_snapshots"] == 1
    latest = client.get("/api/v1/telemetry/market/latest?symbol=EURUSD").json()
    assert latest[0]["symbol"] == "EURUSD"
    assert latest[0]["feed_fresh"] is True


def test_worker_telemetry_persists_account_snapshot(monkeypatch, tmp_path):
    monkeypatch.delenv("TELEMETRY_INGEST_TOKEN", raising=False)
    configure_database(f"sqlite:///{tmp_path / 'telemetry.db'}")
    init_db()
    client = TestClient(create_app(), client=("10.10.1.85", 12345))

    response = client.post(
        "/api/v1/telemetry/worker-snapshot",
        json={
            "worker": "strategy_risk",
            "result": {
                "risk_mode": "monitor_only",
                "auto_execution_enabled": False,
                "positions_count": 0,
                "account": {
                    "login_masked": "***312",
                    "server": "Demo",
                    "currency": "USD",
                    "balance": 200,
                    "equity": 200,
                    "margin_free": 200,
                    "drawdown_pct": 0,
                    "trade_allowed": True,
                },
            },
        },
    )

    assert response.status_code == 202
    assert response.json()["account_snapshots"] == 1
    latest = client.get("/api/v1/telemetry/accounts/latest").json()
    assert latest[0]["login_masked"] == "***312"
    assert latest[0]["auto_execution_enabled"] is False


def test_telemetry_rejects_non_private_client(monkeypatch, tmp_path):
    monkeypatch.delenv("TELEMETRY_INGEST_TOKEN", raising=False)
    configure_database(f"sqlite:///{tmp_path / 'telemetry.db'}")
    init_db()
    client = TestClient(create_app(), client=("203.0.113.10", 12345))

    response = client.post("/api/v1/telemetry/worker-snapshot", json={"worker": "market", "result": {}})

    assert response.status_code == 403

