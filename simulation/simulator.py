from .fake_execution import fake_order_id


def simulate_trade(signal_id: str) -> dict:
    return {"signal_id": signal_id, "order_id": fake_order_id(signal_id), "simulation": True, "label": "SIMULATION"}
