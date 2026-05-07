from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base_agent import AgentMessage, BaseAgent


@dataclass(frozen=True)
class SignalProposal:
    """A proposed signal from the Strategy Agent — never auto-executed."""
    symbol: str
    direction: str  # "buy" or "sell"
    strategy_id: str
    timeframe: str
    confidence: float
    summary: str
    lifecycle_state: str
    governance_status: str
    next_action: str


# Strategy lifecycle states that allow signal generation
_LIFECYCLE_ACTIVE_STATES = frozenset({
    "approved_for_demo_auto",
    "approved_for_manual",
    "approved_for_live_restricted",
    "demo_testing",
})

# Strategy lifecycle states that block signal generation
_LIFECYCLE_BLOCKED_STATES = frozenset({
    "draft",
    "pending_review",
    "rejected",
    "deprecated",
    "suspended",
})


class StrategyAgent(BaseAgent):
    """Proposes trading signals based on strategy rules and lifecycle governance.

    This agent only *proposes* signals — it never executes trades.
    All proposals must pass through Signal Reviewer → Risk Manager →
    Execution Guard before any order is sent.
    """

    name = "Strategy Agent"

    def handle(self, message: AgentMessage) -> AgentMessage:
        """Handle a strategy evaluation request.

        The incoming message.summary should describe the market context.
        Returns a signal proposal or a governance-blocked assessment.
        """
        proposal = self.propose_signal(
            context=message.summary,
            confidence=message.confidence,
        )
        return AgentMessage(
            sender=self.name,
            role="signal_proposal",
            summary=proposal.summary,
            confidence=proposal.confidence,
            risk_status=proposal.governance_status,
        )

    def propose_signal(
        self,
        context: str,
        confidence: float = 0.0,
        symbol: str = "",
        direction: str = "",
        strategy_id: str = "",
        timeframe: str = "M1",
        lifecycle_state: str = "draft",
        quality_score: float = 0.0,
        min_quality_score: float = 0.5,
        market_data_fresh: bool = True,
        trend_status: str = "neutral",
        current_bias: str = "neutral",
    ) -> SignalProposal:
        """Propose a signal based on strategy rules and governance.

        This method is safe by design:
        - It never returns an "execute" action
        - It respects lifecycle governance gates
        - It validates data quality before proposing
        - All proposals require downstream review
        """
        # Check lifecycle governance — blocked states prevent any proposal
        if lifecycle_state in _LIFECYCLE_BLOCKED_STATES:
            return SignalProposal(
                symbol=symbol or "unknown",
                direction="none",
                strategy_id=strategy_id or "unknown",
                timeframe=timeframe,
                confidence=0.0,
                summary=(
                    f"Strategy Agent: strategy '{strategy_id}' is in lifecycle state "
                    f"'{lifecycle_state}' which blocks signal generation. "
                    f"No proposal will be made until governance review is complete."
                ),
                lifecycle_state=lifecycle_state,
                governance_status="lifecycle_blocked",
                next_action="Submit strategy for governance review to advance lifecycle state.",
            )

        # Check if lifecycle state allows proposals
        if lifecycle_state not in _LIFECYCLE_ACTIVE_STATES:
            return SignalProposal(
                symbol=symbol or "unknown",
                direction="none",
                strategy_id=strategy_id or "unknown",
                timeframe=timeframe,
                confidence=0.0,
                summary=(
                    f"Strategy Agent: strategy '{strategy_id}' is in lifecycle state "
                    f"'{lifecycle_state}' which does not permit signal generation. "
                    f"Active states: {', '.join(sorted(_LIFECYCLE_ACTIVE_STATES))}."
                ),
                lifecycle_state=lifecycle_state,
                governance_status="lifecycle_not_active",
                next_action="Promote strategy to an active lifecycle state through governance.",
            )

        # Check market data quality
        if not market_data_fresh:
            return SignalProposal(
                symbol=symbol or "unknown",
                direction="none",
                strategy_id=strategy_id,
                timeframe=timeframe,
                confidence=0.0,
                summary=(
                    f"Strategy Agent: market data for {symbol} is not fresh. "
                    f"Cannot generate a reliable signal proposal."
                ),
                lifecycle_state=lifecycle_state,
                governance_status="data_quality_blocked",
                next_action="Wait for fresh market data before generating signal proposals.",
            )

        # Check quality score threshold
        if quality_score < min_quality_score:
            return SignalProposal(
                symbol=symbol or "unknown",
                direction="none",
                strategy_id=strategy_id,
                timeframe=timeframe,
                confidence=max(0.0, confidence - 0.3),
                summary=(
                    f"Strategy Agent: strategy '{strategy_id}' quality score "
                    f"{quality_score:.2f} is below minimum threshold {min_quality_score:.2f}. "
                    f"Signal proposal withheld."
                ),
                lifecycle_state=lifecycle_state,
                governance_status="quality_below_threshold",
                next_action="Improve strategy parameters or wait for better market conditions.",
            )

        # Determine direction from context if not provided
        if not direction:
            if current_bias in {"bullish", "long"}:
                direction = "buy"
            elif current_bias in {"bearish", "short"}:
                direction = "sell"
            else:
                direction = "neutral"

        # If direction is still neutral, we cannot propose
        if direction not in {"buy", "sell"}:
            return SignalProposal(
                symbol=symbol or "unknown",
                direction="none",
                strategy_id=strategy_id,
                timeframe=timeframe,
                confidence=max(0.0, confidence - 0.2),
                summary=(
                    f"Strategy Agent: no clear directional bias for {symbol} "
                    f"(trend: {trend_status}, bias: {current_bias}). "
                    f"Signal proposal withheld — market conditions unclear."
                ),
                lifecycle_state=lifecycle_state,
                governance_status="no_clear_bias",
                next_action="Wait for clearer market direction before proposing a signal.",
            )

        # Build the proposal — still requires downstream review
        proposal_confidence = min(1.0, confidence * 0.8 + quality_score * 0.2)

        return SignalProposal(
            symbol=symbol,
            direction=direction,
            strategy_id=strategy_id,
            timeframe=timeframe,
            confidence=round(proposal_confidence, 2),
            summary=(
                f"Strategy Agent: proposing {direction} signal for {symbol} on {timeframe} "
                f"using strategy '{strategy_id}' (lifecycle: {lifecycle_state}, "
                f"quality: {quality_score:.2f}, trend: {trend_status}, bias: {current_bias}). "
                f"This proposal requires Signal Reviewer and Risk Manager evaluation "
                f"before reaching Execution Guard."
            ),
            lifecycle_state=lifecycle_state,
            governance_status="proposal_ready_for_review",
            next_action="Submit proposal to Signal Reviewer for quality and risk assessment.",
        )
