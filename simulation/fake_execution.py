def fake_order_id(seed: str) -> str:
    return f"SIM-{abs(hash(seed)) % 1000000:06d}"
