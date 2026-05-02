from __future__ import annotations

from .approval_token import create_approval_token
from .checks import evaluate_required_checks
from .schemas import ExecutionRequest, GuardDecision


def approve_execution(request: ExecutionRequest) -> GuardDecision:
    failures = evaluate_required_checks(request)
    if failures:
        return GuardDecision(approved=False, reasons=tuple(failures), token=None)
    token = create_approval_token(request.account_id, request.strategy_id)
    return GuardDecision(approved=True, reasons=("approved",), token=token)
