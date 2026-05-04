from datetime import UTC, datetime, timedelta
import json

from fastapi.testclient import TestClient

from control.api.db import configure_database, init_db
from control.api.main import create_app
from control.api.models import MarketSnapshot
from control.api.db import SessionLocal
from market_data_quality.indicators import indicator_summary
from market_data_quality.analysis import multi_timeframe_summary, price_action_summary, spread_slippage_summary
from news_feed.adapter import _normalise_fmp_events


def test_market_analysis_helpers():
    snapshots = [
        {"trend": "bullish", "feed_fresh": True, "rates_count": 30, "spread": 12.0},
        {"trend": "bullish", "feed_fresh": True, "rates_count": 25, "spread": 13.0},
        {"trend": "range", "feed_fresh": False, "rates_count": 22, "spread": 14.0},
    ]
    assert multi_timeframe_summary(snapshots)["trend"] == "bullish"
    assert price_action_summary(snapshots[0])["status"] == "ok"
    assert spread_slippage_summary(snapshots[0])["status"] == "ok"


def test_indicator_summary_calculates_baseline_suite():
    rates = []
    price = 1.1000
    for index in range(60):
        price += 0.0001
        rates.append(
            {
                "open": price - 0.00005,
                "high": price + 0.0002,
                "low": price - 0.0002,
                "close": price,
            }
        )
    indicators = indicator_summary(rates)
    assert indicators["ema_20"] is not None
    assert indicators["ema_50"] is not None
    assert indicators["rsi_14"] == 100.0
    assert indicators["atr_14"] is not None
    assert indicators["macd"]["histogram"] is not None
    assert indicators["bollinger_20"]["upper"] > indicators["bollinger_20"]["lower"]


def test_market_analysis_and_news_status_endpoints(monkeypatch, tmp_path):
    monkeypatch.delenv("NEWS_PROVIDER_ENABLED", raising=False)
    monkeypatch.delenv("NEWS_PROVIDER_TYPE", raising=False)
    monkeypatch.delenv("NEWS_CALENDAR_FILE", raising=False)
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
    monkeypatch.setenv("NEWS_PROVIDER_TYPE", "env_window")
    monkeypatch.setenv("NEWS_HIGH_IMPACT_NEXT_MINUTES", "90")
    clear_news = client.get("/api/v1/news/status?symbol=EURUSD").json()
    assert clear_news["news_halt_active"] is False


def test_news_adapter_manual_json_halts_on_high_impact(monkeypatch, tmp_path):
    calendar = tmp_path / "calendar.json"
    event_time = (datetime.now(UTC) + timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
    calendar.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "title": "US CPI",
                        "event_time": event_time,
                        "impact": "high",
                        "currencies": ["USD"],
                        "source": "unit-test",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NEWS_PROVIDER_ENABLED", "true")
    monkeypatch.setenv("NEWS_PROVIDER_TYPE", "manual_json")
    monkeypatch.setenv("NEWS_CALENDAR_FILE", str(calendar))
    app = create_app()
    client = TestClient(app)

    status = client.get("/api/v1/news/status?symbol=EURUSD").json()
    assert status["provider_fresh"] is True
    assert status["news_halt_active"] is True
    assert status["upcoming_high_impact_events"][0]["title"] == "US CPI"

    events = client.get("/api/v1/news/events?symbol=EURUSD").json()
    assert events["events"][0]["currencies"] == ["USD"]


def test_fmp_economic_calendar_normalization_infers_impact_and_currency():
    event_time = (datetime.now(UTC) + timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
    events = _normalise_fmp_events(
        [
            {
                "date": event_time,
                "event": "Nonfarm Payrolls",
                "country": "United States",
                "previous": "180K",
                "estimate": "170K",
            }
        ]
    )

    assert len(events) == 1
    assert events[0].title == "Nonfarm Payrolls"
    assert events[0].currencies == ("USD",)
    assert events[0].impact == "high"
    assert events[0].source == "financial_modeling_prep"
