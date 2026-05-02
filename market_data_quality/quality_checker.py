def data_quality_allows_execution(metrics: dict) -> bool:
    return bool(metrics.get("fresh", False)) and not metrics.get("frozen_feed", False)
