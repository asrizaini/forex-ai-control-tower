import os

from control.api.auth import decode_token, issue_token


def test_tokens_require_configured_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    assert decode_token("anything") is None


def test_hmac_token_round_trip(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    token = issue_token("user-1", "viewer", ("account-1",))["access_token"]
    principal = decode_token(token)
    assert principal is not None
    assert principal.user_id == "user-1"
    assert principal.role == "viewer"
    assert principal.account_ids == ("account-1",)
