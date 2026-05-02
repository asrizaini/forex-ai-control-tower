from fastapi.testclient import TestClient

from control.api.main import app


def test_health_and_docs_available():
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/metrics").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_mobile_bootstrap():
    client = TestClient(app)
    response = client.get("/api/v1/mobile/bootstrap")
    assert response.status_code == 200
    assert response.json()["environment"] == "demo"
