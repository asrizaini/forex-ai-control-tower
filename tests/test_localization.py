from localization.locale_manager import DO_NOT_TRANSLATE, normalize_language
from fastapi.testclient import TestClient

from control.api.main import create_app
from localization.locale_manager import load_locale, translate_key


def test_localization_defaults_and_canonical_terms():
    assert normalize_language("ms-MY") == "ms-MY"
    assert normalize_language("id") == "en"
    assert "EURUSD" in DO_NOT_TRANSLATE
    assert "strategy_id" in DO_NOT_TRANSLATE


def test_locale_loading_and_translation_api():
    assert load_locale("ms-MY", "dashboard")["system_health"] == "Kesihatan Sistem"
    assert translate_key("dashboard", "risk_status", "ms-MY") == "Status Risiko"
    app = create_app()
    client = TestClient(app)
    locale = client.get("/api/v1/localization/locales/ms-MY/dashboard").json()
    assert locale["messages"]["control_plane"] == "Panel Kawalan"
    detected = client.post("/api/v1/localization/detect", json={"text": "Semak risiko akaun dagangan"}).json()
    assert detected["language"] == "ms-MY"
