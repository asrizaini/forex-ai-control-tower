from __future__ import annotations

from dataclasses import dataclass


QUALITY_WEIGHTS = {
    "drawdown_control": 0.30,
    "profit_factor": 0.25,
    "forward_consistency": 0.20,
    "win_rate_stability": 0.15,
    "execution_quality": 0.10,
}


@dataclass(frozen=True)
class StrategyLabScore:
    quality_score: float
    drawdown_control: float
    profit_factor_score: float
    forward_consistency: float
    win_rate_stability: float
    execution_quality: float


def quality_score(
    *,
    drawdown_pct: float,
    profit_factor: float,
    forward_consistency: float,
    win_rate_stability: float,
    execution_quality: float,
) -> StrategyLabScore:
    drawdown_control = max(0.0, min(1.0, 1.0 - (drawdown_pct / 30.0)))
    profit_factor_score = max(0.0, min(1.0, (profit_factor - 1.0) / 2.0))
    components = {
        "drawdown_control": drawdown_control,
        "profit_factor_score": profit_factor_score,
        "forward_consistency": max(0.0, min(1.0, forward_consistency)),
        "win_rate_stability": max(0.0, min(1.0, win_rate_stability)),
        "execution_quality": max(0.0, min(1.0, execution_quality)),
    }
    weighted_components = {
        "drawdown_control": components["drawdown_control"],
        "profit_factor": components["profit_factor_score"],
        "forward_consistency": components["forward_consistency"],
        "win_rate_stability": components["win_rate_stability"],
        "execution_quality": components["execution_quality"],
    }
    score = sum(weighted_components[name] * weight for name, weight in QUALITY_WEIGHTS.items()) * 100
    return StrategyLabScore(round(score, 2), **components)


def deterministic_backtest_result(strategy_id: str, symbol: str, timeframe: str) -> dict:
    seed = sum(ord(char) for char in f"{strategy_id}:{symbol}:{timeframe}")
    profit_factor = round(1.05 + (seed % 90) / 100, 2)
    drawdown_pct = round(4.0 + (seed % 18), 2)
    win_rate = round(0.42 + (seed % 18) / 100, 2)
    score = quality_score(
        drawdown_pct=drawdown_pct,
        profit_factor=profit_factor,
        forward_consistency=0.0,
        win_rate_stability=win_rate,
        execution_quality=0.65,
    )
    return {
        "profit_factor": profit_factor,
        "drawdown_pct": drawdown_pct,
        "win_rate": win_rate,
        "quality_score": score.quality_score,
        "score_components": score.__dict__,
        "mock_safe": True,
        "note": "Deterministic scaffold result; replace with historical engine before strategy promotion.",
    }


SCHEDULES = {
    "every_1_minute": ["market_account_health", "open_trade_risk", "spread_slippage"],
    "every_5_minutes": ["signal_rescoring", "technical_condition_updates"],
    "every_15_minutes": ["news_fundamental_refresh"],
    "daily": ["strategy_performance_report", "account_report", "drawdown_report"],
    "weekend": ["deep_backtest", "parameter_tuning", "strategy_version_comparison"],
}
