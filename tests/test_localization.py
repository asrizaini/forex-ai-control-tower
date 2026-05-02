from localization.locale_manager import DO_NOT_TRANSLATE, normalize_language


def test_localization_defaults_and_canonical_terms():
    assert normalize_language("ms-MY") == "ms-MY"
    assert normalize_language("id") == "en"
    assert "EURUSD" in DO_NOT_TRANSLATE
    assert "strategy_id" in DO_NOT_TRANSLATE
