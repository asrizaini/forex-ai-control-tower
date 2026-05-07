from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base_agent import AgentMessage, BaseAgent


@dataclass(frozen=True)
class RiskEvaluation:
    """Structured risk evaluation result — never triggers execution directly."""
    risk_status: str
    summary: str
    confidence: float
    blockers: tuple[str, ...]
    next_action: str


class RiskManagerAgent(BaseAgent):
    """Evaluates risk against control-plane policies.

    This agent only *evaluates* and *reports* — it never approves, executes,
    or modifies risk policies. All execution decisions flow through the
    Execution Guard, which is the sole gatekeeper.
    """

    name = "Risk Manager"

    def handle(self, message: AgentMessage) -> AgentMessage:
        """Handle a risk evaluation request.

        The incoming message.summary should describe the risk context.
        The message.risk_status carries the current risk posture.
        Returns a structured risk assessment as an AgentMessage.
        """
        evaluation = self.evaluate_risk(
            context=message.summary,
            current_risk_status=message.risk_status,
            confidence=message.confidence,
        )
        return AgentMessage(
            sender=self.name,
            role="risk_evaluation",
            summary=evaluation.summary,
            confidence=evaluation.confidence,
            risk_status=evaluation.risk_status,
        )

    def evaluate_risk(
        self,
        context: str,
        current_risk_status: str = "unknown",
        confidence: float = 0.0,
        kill_switch_active: bool = False,
        daily_loss_pct: float = 0.0,
        max_daily_loss_pct: float = 5.0,
        weekly_loss_pct: float = 0.0,
        max_weekly_loss_pct: float = 10.0,
        open_trades: int = 0,
        max_open_trades: int = 3,
        news_halt_active: bool = False,
        trading_mode: str = "monitor_only",
    ) -> RiskEvaluation:
        """Evaluate risk conditions and return a structured assessment.

        This method is safe by design:
        - It never returns an "approved" status
        - It never triggers execution
        - It only reports blockers and recommendations
        - All execution decisions go through Execution Guard
        """
        blockers: list[str] = []

        # Check kill switch first — always blocks
        if kill_switch_active:
            blockers.append("kill_switch_active")

        # Check trading mode — monitor_only and emergency_halt always block
        if trading_mode in {"monitor_only", "alert_only", "emergency_halt"}:
            blockers.append(f"trading_mode_blocks:{trading_mode}")

        # Check daily loss limit
        if daily_loss_pct > max_daily_loss_pct:
            blockers.append("daily_loss_limit_exceeded")

        # Check weekly loss limit
        if weekly_loss_pct > max_weekly_loss_pct:
            blockers.append("weekly_loss_limit_exceeded")

        # Check open trade count
        if open_trades >= max_open_trades:
            blockers.append("max_open_trades_reached")

        # Check news halt
        if news_halt_active:
            blockers.append("news_halt_active")

        # Determine risk status
        if blockers:
            risk_status = "risk_blocked"
            summary = (
                f"Risk Manager evaluated: {len(blockers)} blocker(s) found — "
                + "; ".join(blockers)
                + ". No execution is permitted while these conditions persist."
            )
            next_action = "Resolve risk blockers before any trade proposal can proceed to Execution Guard review."
        elif current_risk_status in {"execution_guarded_monitor_only", "review_complete_no_execution"}:
            risk_status = "risk_reviewed_no_execution"
            summary = (
                f"Risk Manager reviewed: no active blockers, but the system remains in monitor-only mode. "
                f"Daily loss {daily_loss_pct:.1f}%/{max_daily_loss_pct:.1f}%, "
                f"weekly loss {weekly_loss_pct:.1f}%/{max_weekly_loss_pct:.1f}%, "
                f"open trades {open_trades}/{max_open_trades}."
            )
            next_action = "Enable demo_auto trading mode and pass Execution Guard checks before any order can be sent."
        else:
            risk_status = "risk_conditions_acceptable"
            summary = (
                f"Risk Manager reviewed: no blockers detected. "
                f"Daily loss {daily_loss_pct:.1f}%/{max_daily_loss_pct:.1f}%, "
                f"weekly loss {weekly_loss_pct:.1f}%/{max_weekly_loss_pct:.1f}%, "
                f"open trades {open_trades}/{max_open_trades}. "
                f"Execution remains governed by Execution Guard."
            )
            next_action = "Signal may proceed to Execution Guard for final approval. Risk Manager does not authorize execution."

        # Confidence reflects how complete the risk picture is
        eval_confidence = min(1.0, confidence + 0.1) if not blockers else max(0.0, confidence - 0.2)

        return RiskEvaluation(
            risk_status=risk_status,
            summary=summary,
            confidence=round(eval_confidence, 2),
            blockers=tuple(blockers),
            next_action=next_action,
        )
