from fastapi.testclient import TestClient

from mt5_bridge.bridge_service import app


def test_order_send_requires_order_check_and_guard_token():
    client = TestClient(app)
    payload = {"client_order_id": "c1", "account_id": "a1", "symbol": "EURUSD", "side": "BUY", "volume": 0.1}
    response = client.post("/order/send", json=payload)
    assert response.status_code == 409

    checked = client.post("/order/check", json=payload)
    assert checked.status_code == 503
    response = client.post("/order/send", json=payload)
    assert response.status_code == 409
