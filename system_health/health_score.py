def calculate_health_score(checks: dict[str, bool]) -> int:
    if not checks:
        return 0
    return round(sum(1 for ok in checks.values() if ok) / len(checks) * 100)


def execution_allowed(score: int, mt5_bridge_online: bool = True, risk_engine_online: bool = True) -> bool:
    return score >= 70 and mt5_bridge_online and risk_engine_online
