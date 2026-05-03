from fastapi.testclient import TestClient

from control.api.db import configure_database, init_db
from control.api.main import create_app


def test_alertmanager_webhook_creates_notification_event(monkeypatch, tmp_path):
    monkeypatch.setenv("ALERTMANAGER_WEBHOOK_TOKEN", "unit-alert-token")
    configure_database(f"sqlite:///{tmp_path / 'alerts.db'}")
    init_db()
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/notifications/monitoring/webhook",
        headers={"X-Alertmanager-Token": "unit-alert-token"},
        json={
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "ForexControlApiDown", "severity": "critical"},
                    "annotations": {"summary": "Control API is down", "description": "Unit test alert."},
                }
            ]
        },
    )

    assert response.status_code == 202
    assert response.json()["events_created"] == 1
    events = client.get("/api/v1/notifications/events").json()
    assert events[0]["notification_type"] == "system_alert"


def test_market_telemetry_persists_historical_candles(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEMETRY_INGEST_TOKEN", "unit-telemetry-token")
    configure_database(f"sqlite:///{tmp_path / 'candles.db'}")
    init_db()
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/telemetry/worker-snapshot",
        headers={"X-Telemetry-Token": "unit-telemetry-token"},
        json={
            "worker": "market",
            "result": {
                "data_quality": "ok",
                "snapshots": [
                    {
                        "symbol": "EURUSD",
                        "timeframe": "M1",
                        "trend": "bullish",
                        "feed_fresh": True,
                        "rates_count": 1,
                        "rates": [
                            {
                                "time": "2026-05-04T00:00:00Z",
                                "open": 1.1,
                                "high": 1.2,
                                "low": 1.0,
                                "close": 1.15,
                                "tick_volume": 10,
                                "spread": 2,
                            }
                        ],
                    }
                ],
            },
        },
    )

    assert response.status_code == 202
    assert response.json()["historical_candles"] == 1
    candles = client.get("/api/v1/telemetry/market/candles?symbol=EURUSD&timeframe=M1").json()
    assert candles[0]["close"] == 1.15
