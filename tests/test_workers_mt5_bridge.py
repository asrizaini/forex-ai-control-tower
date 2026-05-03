from workers import market_worker, strategy_risk_worker
from agent_theater.dialogue_templates import market_dialogue


def test_market_worker_summarizes_mt5_bridge_data(monkeypatch):
    monkeypatch.setattr(market_worker, "bridge_health", lambda: {"ok": True, "body": {"mt5_connected": True, "status": "ok"}})
    monkeypatch.setattr(market_worker, "bridge_symbols", lambda: {"ok": True, "body": {"symbols": ["EURUSD"]}})
    monkeypatch.setattr(market_worker, "configured_watchlist", lambda: ["EURUSD"])
    monkeypatch.setattr(
        market_worker,
        "bridge_rates",
        lambda _symbol: {"ok": True, "body": {"rates": [{"close": float(index)} for index in range(1, 31)]}},
    )
    monkeypatch.setattr(market_worker, "bridge_ticks", lambda _symbol: {"ok": True, "body": {"tick": {"bid": 1.1, "ask": 1.1002, "time": 4_102_444_800}}})

    result = market_worker.run_market_worker_once()

    assert result["status"] == "ready"
    assert result["symbols_monitored"] == ["EURUSD"]
    assert result["snapshots"][0]["trend"] == "bullish"
    assert result["snapshots"][0]["feed_fresh"] is True


def test_strategy_risk_worker_masks_account_login(monkeypatch):
    monkeypatch.setattr(strategy_risk_worker, "bridge_health", lambda: {"ok": True, "body": {"mt5_connected": True}})
    monkeypatch.setattr(
        strategy_risk_worker,
        "bridge_account",
        lambda: {
            "ok": True,
            "body": {
                "login": 123456789,
                "server": "Demo-Server",
                "currency": "USD",
                "balance": 10000,
                "equity": 9900,
                "margin_free": 9800,
                "trade_allowed": True,
            },
        },
    )
    monkeypatch.setattr(strategy_risk_worker, "bridge_positions", lambda: {"ok": True, "body": {"positions": [{"ticket": 1}]}})

    result = strategy_risk_worker.run_strategy_risk_worker_once()

    assert result["status"] == "ready"
    assert result["account"]["login_masked"] == "***789"
    assert result["account"]["drawdown_pct"] == 1.0
    assert result["positions_count"] == 1
    assert result["auto_execution_enabled"] is False


def test_market_dialogue_blocks_stale_data_signal_language():
    events = market_dialogue(
        "market",
        {
            "bridge_connected": True,
            "data_quality": "limited",
            "snapshots": [
                {
                    "symbol": "EURUSD",
                    "feed_fresh": False,
                    "rates_count": 0,
                    "freshness_seconds": 999,
                    "trend": "insufficient_candles",
                    "spread": 0.0002,
                }
            ],
        },
    )

    assert "market data is limited" in events[0]["summary"]
    assert "blocking signal commentary" in events[1]["summary"]
