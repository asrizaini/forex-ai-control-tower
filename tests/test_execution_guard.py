from execution_guard.guard import approve_execution
from execution_guard.schemas import ExecutionRequest


def test_monitor_only_blocks_execution_by_default():
    decision = approve_execution(ExecutionRequest(account_id="a1", strategy_id="s1", symbol="EURUSD", side="BUY", volume=0.1))
    assert not decision.approved
    assert any("monitor_only" in reason for reason in decision.reasons)
