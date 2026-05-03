from fastapi.testclient import TestClient

from control.api.db import configure_database, init_db
from control.api.main import create_app


def _client(tmp_path):
    configure_database(f"sqlite:///{tmp_path / 'observability.db'}")
    init_db()
    return TestClient(create_app())


def test_custom_observability_metrics_are_exposed(tmp_path):
    client = _client(tmp_path)

    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "forex_api_requests_total" in body
    assert "forex_control_plane_records" in body
    assert "forex_agent_tasks" in body
    assert "forex_market_data_stale_symbols" in body


def test_observability_status_endpoint_lists_operator_metrics(tmp_path):
    client = _client(tmp_path)

    response = client.get("/api/v1/system/observability")

    assert response.status_code == 200
    body = response.json()
    assert body["structured_api_access_logs"] is True
    assert "forex_api_request_latency_seconds" in body["prometheus_custom_metrics"]
    assert isinstance(body["agent_tasks"], list)
