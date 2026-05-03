from fastapi.testclient import TestClient

from control.api.db import configure_database, init_db
from control.api.main import create_app
from control.api.models import MarketSnapshot
from control.api.db import SessionLocal
from market_data_quality.analysis import multi_timeframe_summary, price_action_summary, spread_slippage_summary


def test_market_analysis_helpers():
    snapshots = [
        {"trend": "bullish", "feed_fresh": True, "rates_count": 30, "spread": 12.0},
        {"trend": "bullish", "feed_fresh": True, "rates_count": 25, "spread": 13.0},
        {"trend": "range", "feed_fresh": False, "rates_count": 22, "spread": 14.0},
    ]
    assert multi_timeframe_summary(snapshots)["trend"] == "bullish"
    assert price_action_summary(snapshots[0])["status"] == "ok"
    assert spread_slippage_summary(snapshots[0])["status"] == "ok"


def test_market_analysis_and_news_status_endpoints(monkeypatch, tmp_path):
    configure_database(f"sqlite:///{tmp_path / 'market.db'}")
    init_db()
    db = SessionLocal()
    db.add(
        MarketSnapshot(
            worker="market",
            symbol="EURUSD",
            trend="bullish",
            spread=12.0,
            freshness_seconds=2,
            rates_count=30,
            feed_fresh=True,
            data_quality="fresh",
            payload_json={"slippage_points": 1.0},
        )
    )
    db.commit()
    db.close()
    app = create_app()
    client = TestClient(app)

    analysis = client.get("/api/v1/telemetry/market/EURUSD/analysis").json()
    assert analysis["execution_allowed_by_market_data"] is True
    assert analysis["multi_timeframe"]["trend"] == "bullish"

    default_news = client.get("/api/v1/news/status?symbol=EURUSD").json()
    assert default_news["news_halt_active"] is True

    monkeypatch.setenv("NEWS_PROVIDER_ENABLED", "true")
    monkeypatch.setenv("NEWS_HIGH_IMPACT_NEXT_MINUTES", "90")
    clear_news = client.get("/api/v1/news/status?symbol=EURUSD").json()
    assert clear_news["news_halt_active"] is False
