from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base_agent import AgentMessage, BaseAgent


@dataclass(frozen=True)
class SignalReview:
    """A signal review result — never auto-executes, only recommends."""
    review_status: str  # "approved_for_review", "requires_risk_review", "rejected"
    summary: str
    confidence: float
    risk_flags: tuple[str, ...]
    governance_flags: tuple[str, ...]
    next_action: str


# Signal statuses that are eligible for review
_REVIEWABLE_SIGNAL_STATUSES = frozenset({
    "active",
    "pending",
    "generated",
})

# Signal statuses that are blocked from review
_BLOCKED_SIGNAL_STATUSES = frozenset({
    "blocked",
    "stale",
    "no_signal",
    "expired",
    "cancelled",
})


class SignalReviewerAgent(BaseAgent):
    """Reviews signal quality and validates against risk and governance.

    This agent is the second gate in the signal pipeline:
    Strategy Agent → Signal Reviewer → Risk Manager → Execution Guard

    It never approves execution — it only marks signals as ready for
    further review or flags them for rejection.
    """

    name = "Signal Reviewer"

    def handle(self, message: AgentMessage) -> AgentMessage:
        """Handle a signal review request.

        The incoming message.summary should describe the signal context.
        Returns a signal review assessment as an AgentMessage.
        """
        review = self.review_signal(
            context=message.summary,
            confidence=message.confidence,
            risk_status=message.risk_status,
        )
        return AgentMessage(
            sender=self.name,
            role="signal_review",
            summary=review.summary,
            confidence=review.confidence,
            risk_status=review.review_status,
        )

    def review_signal(
        self,
        context: str,
        confidence: float = 0.0,
        risk_status: str = "unknown",
        signal_status: str = "active",
        direction: str = "",
        symbol: str = "",
        strategy_id: str = "",
        timeframe: str = "M1",
        min_confidence: float = 0.4,
        max_spread_points: float = 30.0,
        spread_points: float = 0.0,
        news_halt_active: bool = False,
        market_data_fresh: bool = True,
        duplicate_signal: bool = False,
        correlation_conflict: bool = False,
        strategy_lifecycle_state: str = "draft",
        quality_score: float = 0.0,
    ) -> SignalReview:
        """Review a signal for quality, risk, and governance compliance.

        This method is safe by design:
        - It never returns "execute" or "approved_for_execution"
        - It only recommends "approved_for_review" which means the signal
          can proceed to Risk Manager evaluation
        - All execution decisions are made by Execution Guard
        """
        risk_flags: list[str] = []
        governance_flags: list[str] = []

        # Check signal status — blocked statuses cannot be reviewed
        if signal_status in _BLOCKED_SIGNAL_STATUSES:
            return SignalReview(
                review_status="rejected",
                summary=(
                    f"Signal Reviewer: signal for {symbol} has status '{signal_status}' "
                    f"which is not reviewable. Blocked statuses: "
                    f"{', '.join(sorted(_BLOCKED_SIGNAL_STATUSES))}."
                ),
                confidence=0.0,
                risk_flags=(),
                governance_flags=(f"signal_status_blocked:{signal_status}",),
                next_action="Generate a new signal with active status before review.",
            )

        # Check direction validity
        if direction not in {"buy", "sell"}:
            return SignalReview(
                review_status="rejected",
                summary=(
                    f"Signal Reviewer: signal for {symbol} has invalid direction "
                    f"'{direction}'. Only 'buy' or 'sell' are accepted."
                ),
                confidence=0.0,
                risk_flags=(),
                governance_flags=("invalid_direction",),
                next_action="Signal must have a valid direction (buy/sell) to be reviewed.",
            )

        # Check strategy lifecycle governance
        if strategy_lifecycle_state in {"draft", "pending_review", "rejected", "deprecated", "suspended"}:
            governance_flags.append(f"strategy_lifecycle_blocked:{strategy_lifecycle_state}")

        # Check news halt
        if news_halt_active:
            risk_flags.append("news_halt_active")

        # Check market data freshness
        if not market_data_fresh:
            risk_flags.append("stale_market_data")

        # Check spread
        if spread_points > max_spread_points:
            risk_flags.append(f"excessive_spread:{spread_points:.1f}pt>{max_spread_points:.1f}pt")

        # Check for duplicate signals
        if duplicate_signal:
            risk_flags.append("duplicate_signal")

        # Check for correlation conflicts
        if correlation_conflict:
            risk_flags.append("correlation_conflict")

        # Check confidence threshold
        if confidence < min_confidence:
            risk_flags.append(f"low_confidence:{confidence:.2f}<{min_confidence:.2f}")

        # Check quality score
        if quality_score < 0.3:
            governance_flags.append(f"low_quality_score:{quality_score:.2f}")

        # Determine review status based on flags
        if governance_flags:
            # Governance flags block the signal entirely
            return SignalReview(
                review_status="rejected",
                summary=(
                    f"Signal Reviewer: {direction} signal for {symbol} ({strategy_id}) "
                    f"REJECTED due to governance issues: "
                    + "; ".join(governance_flags)
                    + ". This signal cannot proceed to Risk Manager review."
                ),
                confidence=max(0.0, confidence - 0.3),
                risk_flags=tuple(risk_flags),
                governance_flags=tuple(governance_flags),
                next_action="Resolve governance issues before resubmitting signal for review.",
            )

        if risk_flags:
            # Risk flags require Risk Manager evaluation — signal is not rejected
            # but needs further review
            return SignalReview(
                review_status="requires_risk_review",
                summary=(
                    f"Signal Reviewer: {direction} signal for {symbol} ({strategy_id}) "
                    f"has {len(risk_flags)} risk flag(s): "
                    + "; ".join(risk_flags)
                    + f". Requires Risk Manager evaluation before any execution consideration."
                ),
                confidence=max(0.0, confidence - 0.1),
                risk_flags=tuple(risk_flags),
                governance_flags=tuple(governance_flags),
                next_action="Submit to Risk Manager for risk assessment before Execution Guard review.",
            )

        # No flags — signal passes initial review but still needs Risk Manager + Execution Guard
        return SignalReview(
            review_status="approved_for_review",
            summary=(
                f"Signal Reviewer: {direction} signal for {symbol} ({strategy_id}) "
                f"passed initial review (confidence: {confidence:.2f}, quality: {quality_score:.2f}). "
                f"This signal is cleared for Risk Manager evaluation. "
                f"Execution Guard remains the final gatekeeper."
            ),
            confidence=min(1.0, confidence + 0.05),
            risk_flags=(),
            governance_flags=(),
            next_action="Submit to Risk Manager for risk assessment, then to Execution Guard for final decision.",
        )
