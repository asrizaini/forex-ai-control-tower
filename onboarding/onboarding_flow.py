REQUIRED_STEPS = ["user_created", "account_assigned", "strategies_assigned", "risk_notice_accepted"]

def complete(steps: set[str]) -> bool:
    return set(REQUIRED_STEPS).issubset(steps)
