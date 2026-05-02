from control.api.permissions import has_permission
from simulation.simulator import simulate_trade
from system_health.health_score import execution_allowed


def test_permissions_deny_by_default():
    assert not has_permission("viewer", "system:halt")
    assert not has_permission("unknown", "dashboard:read")


def test_health_threshold_blocks_execution():
    assert not execution_allowed(69)
    assert not execution_allowed(100, mt5_bridge_online=False)


def test_simulation_trade_is_labeled():
    trade = simulate_trade("sig-1")
    assert trade["simulation"] is True
    assert trade["label"] == "SIMULATION"
