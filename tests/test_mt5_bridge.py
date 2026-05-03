from fastapi.testclient import TestClient

from mt5_bridge.account_profile import AccountProfile, load_account_profiles, profile_for_account, save_account_profiles
from mt5_bridge.bridge_service import app


def test_order_send_requires_order_check_and_guard_token():
    client = TestClient(app)
    payload = {"client_order_id": "c1", "account_id": "a1", "symbol": "EURUSD", "side": "BUY", "volume": 0.1}
    response = client.post("/order/send", json=payload)
    assert response.status_code in {401, 503}
    checked = client.post("/order/check", json=payload)
    assert checked.status_code in {401, 503}
    response = client.post("/order/send", json=payload)
    assert response.status_code in {401, 503}


def test_account_profiles_persist_without_credentials(tmp_path):
    profile_file = tmp_path / "profiles.json"
    save_account_profiles(
        [AccountProfile(account_id="demo_main", terminal_port=8501, environment="demo", trading_mode="monitor_only")],
        profile_file,
    )

    profiles = load_account_profiles(profile_file)
    assert profiles[0].account_id == "demo_main"
    assert profile_for_account("demo_main", profile_file).terminal_port == 8501
    assert "password" not in profile_file.read_text(encoding="utf-8").lower()


def test_bridge_account_profile_endpoints_require_token_and_block_live(monkeypatch, tmp_path):
    monkeypatch.setenv("BRIDGE_API_TOKEN", "unit-test-bridge-token")
    monkeypatch.setenv("MT5_ACCOUNT_PROFILES_FILE", str(tmp_path / "profiles.json"))
    client = TestClient(app)

    unauthorized = client.get("/accounts/profiles")
    assert unauthorized.status_code == 401

    created = client.post(
        "/accounts/profiles",
        headers={"x-bridge-token": "unit-test-bridge-token"},
        json={"account_id": "demo_main", "terminal_port": 8501, "environment": "demo", "trading_mode": "monitor_only"},
    )
    assert created.status_code == 200

    blocked = client.post(
        "/accounts/profiles",
        headers={"x-bridge-token": "unit-test-bridge-token"},
        json={"account_id": "live_main", "terminal_port": 8502, "environment": "production-live", "trading_mode": "manual_live"},
    )
    assert blocked.status_code == 403

    route = client.get("/accounts/demo_main/route", headers={"x-bridge-token": "unit-test-bridge-token"})
    assert route.status_code == 200
    assert route.json()["terminal_port"] == 8501
