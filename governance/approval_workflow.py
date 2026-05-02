def requires_admin_approval(action: str) -> bool:
    return action in {"live_mode", "strategy_promotion", "paid_llm_threshold", "system_update"}
