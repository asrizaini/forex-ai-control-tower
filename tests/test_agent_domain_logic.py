"""Tests for the three critical agent domain logic implementations:
RiskManagerAgent, StrategyAgent, SignalReviewerAgent.

These tests verify that agents:
1. Never auto-execute trades
2. Respect safety constraints (monitor_only, kill switches, governance)
3. Produce structured, auditable outputs
4. Handle edge cases correctly
"""

from agents.risk_manager_agent import RiskManagerAgent, RiskEvaluation
from agents.signal_reviewer_agent import SignalReviewerAgent, SignalReview
from agents.strategy_agent import StrategyAgent, SignalProposal
from agents.base_agent import AgentMessage, BaseAgent


# ─── RiskManagerAgent Tests ───────────────────────────────────────────────────


class TestRiskManagerAgent:
    """Test RiskManagerAgent domain logic."""

    def test_agent_name(self):
        agent = RiskManagerAgent()
        assert agent.name == "Risk Manager"

    def test_handle_returns_agent_message(self):
        agent = RiskManagerAgent()
        msg = AgentMessage(
            sender="Orchestrator Agent",
            role="task_dispatch",
            summary="Evaluate risk for EURUSD buy signal",
            confidence=0.5,
            risk_status="unknown",
        )
        result = agent.handle(msg)
        assert isinstance(result, AgentMessage)
        assert result.sender == "Risk Manager"
        assert result.role == "risk_evaluation"

    def test_kill_switch_always_blocks(self):
        agent = RiskManagerAgent()
        result = agent.evaluate_risk(
            context="test",
            kill_switch_active=True,
            daily_loss_pct=0.0,
            weekly_loss_pct=0.0,
            open_trades=0,
        )
        assert result.risk_status == "risk_blocked"
        assert "kill_switch_active" in result.blockers

    def test_monitor_only_mode_blocks(self):
        agent = RiskManagerAgent()
        result = agent.evaluate_risk(
            context="test",
            trading_mode="monitor_only",
        )
        assert result.risk_status == "risk_blocked"
        assert any("monitor_only" in b for b in result.blockers)

    def test_emergency_halt_mode_blocks(self):
        agent = RiskManagerAgent()
        result = agent.evaluate_risk(
            context="test",
            trading_mode="emergency_halt",
        )
        assert result.risk_status == "risk_blocked"
        assert any("emergency_halt" in b for b in result.blockers)

    def test_daily_loss_limit_exceeded(self):
        agent = RiskManagerAgent()
        result = agent.evaluate_risk(
            context="test",
            daily_loss_pct=6.0,
            max_daily_loss_pct=5.0,
            trading_mode="demo_auto",
        )
        assert result.risk_status == "risk_blocked"
        assert "daily_loss_limit_exceeded" in result.blockers

    def test_weekly_loss_limit_exceeded(self):
        agent = RiskManagerAgent()
        result = agent.evaluate_risk(
            context="test",
            weekly_loss_pct=12.0,
            max_weekly_loss_pct=10.0,
            trading_mode="demo_auto",
        )
        assert result.risk_status == "risk_blocked"
        assert "weekly_loss_limit_exceeded" in result.blockers

    def test_max_open_trades_reached(self):
        agent = RiskManagerAgent()
        result = agent.evaluate_risk(
            context="test",
            open_trades=5,
            max_open_trades=3,
            trading_mode="demo_auto",
        )
        assert result.risk_status == "risk_blocked"
        assert "max_open_trades_reached" in result.blockers

    def test_news_halt_active(self):
        agent = RiskManagerAgent()
        result = agent.evaluate_risk(
            context="test",
            news_halt_active=True,
            trading_mode="demo_auto",
        )
        assert result.risk_status == "risk_blocked"
        assert "news_halt_active" in result.blockers

    def test_acceptable_conditions_with_demo_auto(self):
        agent = RiskManagerAgent()
        result = agent.evaluate_risk(
            context="test",
            trading_mode="demo_auto",
            daily_loss_pct=1.0,
            max_daily_loss_pct=5.0,
            weekly_loss_pct=3.0,
            max_weekly_loss_pct=10.0,
            open_trades=1,
            max_open_trades=3,
        )
        assert result.risk_status == "risk_conditions_acceptable"
        assert len(result.blockers) == 0
        # Even with acceptable conditions, the agent does NOT authorize execution
        assert "Execution Guard" in result.next_action

    def test_monitor_only_even_with_acceptable_risk(self):
        agent = RiskManagerAgent()
        result = agent.evaluate_risk(
            context="test",
            trading_mode="monitor_only",
            daily_loss_pct=0.0,
            weekly_loss_pct=0.0,
            open_trades=0,
        )
        # monitor_only should still block
        assert result.risk_status == "risk_blocked"

    def test_multiple_blockers(self):
        agent = RiskManagerAgent()
        result = agent.evaluate_risk(
            context="test",
            kill_switch_active=True,
            daily_loss_pct=10.0,
            max_daily_loss_pct=5.0,
            news_halt_active=True,
            trading_mode="emergency_halt",
        )
        assert result.risk_status == "risk_blocked"
        assert len(result.blockers) >= 3

    def test_never_approves_execution(self):
        """Safety invariant: RiskManagerAgent never returns an 'approved' status."""
        agent = RiskManagerAgent()
        for mode in ["monitor_only", "demo_auto", "alert_only", "emergency_halt"]:
            result = agent.evaluate_risk(context="test", trading_mode=mode)
            assert "approved" not in result.risk_status, (
                f"RiskManagerAgent must never approve execution, got: {result.risk_status}"
            )


# ─── StrategyAgent Tests ──────────────────────────────────────────────────────


class TestStrategyAgent:
    """Test StrategyAgent domain logic."""

    def test_agent_name(self):
        agent = StrategyAgent()
        assert agent.name == "Strategy Agent"

    def test_handle_returns_agent_message(self):
        agent = StrategyAgent()
        msg = AgentMessage(
            sender="Orchestrator Agent",
            role="task_dispatch",
            summary="Generate signal for EURUSD",
            confidence=0.5,
            risk_status="unknown",
        )
        result = agent.handle(msg)
        assert isinstance(result, AgentMessage)
        assert result.sender == "Strategy Agent"
        assert result.role == "signal_proposal"

    def test_draft_lifecycle_blocks_proposal(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            strategy_id="test_strategy",
            lifecycle_state="draft",
        )
        assert result.governance_status == "lifecycle_blocked"
        assert result.direction == "none"
        assert result.confidence == 0.0

    def test_pending_review_lifecycle_blocks(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            strategy_id="test_strategy",
            lifecycle_state="pending_review",
        )
        assert result.governance_status == "lifecycle_blocked"

    def test_rejected_lifecycle_blocks(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            strategy_id="test_strategy",
            lifecycle_state="rejected",
        )
        assert result.governance_status == "lifecycle_blocked"

    def test_deprecated_lifecycle_blocks(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            strategy_id="test_strategy",
            lifecycle_state="deprecated",
        )
        assert result.governance_status == "lifecycle_blocked"

    def test_suspended_lifecycle_blocks(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            strategy_id="test_strategy",
            lifecycle_state="suspended",
        )
        assert result.governance_status == "lifecycle_blocked"

    def test_unknown_lifecycle_not_active(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            strategy_id="test_strategy",
            lifecycle_state="unknown_state",
        )
        assert result.governance_status == "lifecycle_not_active"

    def test_approved_lifecycle_allows_proposal(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            symbol="EURUSD",
            direction="buy",
            strategy_id="trend_pullback_v1",
            timeframe="M1",
            lifecycle_state="approved_for_demo_auto",
            quality_score=0.8,
            market_data_fresh=True,
            trend_status="bullish",
            current_bias="bullish",
            confidence=0.7,
        )
        assert result.governance_status == "proposal_ready_for_review"
        assert result.direction == "buy"
        assert result.confidence > 0.0

    def test_stale_market_data_blocks(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            symbol="EURUSD",
            strategy_id="trend_pullback_v1",
            lifecycle_state="approved_for_demo_auto",
            market_data_fresh=False,
        )
        assert result.governance_status == "data_quality_blocked"
        assert result.direction == "none"

    def test_low_quality_score_blocks(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            symbol="EURUSD",
            strategy_id="trend_pullback_v1",
            lifecycle_state="approved_for_demo_auto",
            quality_score=0.2,
            min_quality_score=0.5,
            market_data_fresh=True,
        )
        assert result.governance_status == "quality_below_threshold"

    def test_no_clear_bias_withholds_proposal(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            symbol="EURUSD",
            strategy_id="trend_pullback_v1",
            lifecycle_state="approved_for_demo_auto",
            quality_score=0.8,
            market_data_fresh=True,
            direction="",
            trend_status="neutral",
            current_bias="neutral",
        )
        assert result.governance_status == "no_clear_bias"
        assert result.direction == "none"

    def test_bullish_bias_sets_buy_direction(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            symbol="EURUSD",
            strategy_id="trend_pullback_v1",
            lifecycle_state="approved_for_demo_auto",
            quality_score=0.8,
            market_data_fresh=True,
            direction="",
            trend_status="bullish",
            current_bias="bullish",
        )
        assert result.direction == "buy"

    def test_bearish_bias_sets_sell_direction(self):
        agent = StrategyAgent()
        result = agent.propose_signal(
            context="test",
            symbol="EURUSD",
            strategy_id="trend_pullback_v1",
            lifecycle_state="approved_for_demo_auto",
            quality_score=0.8,
            market_data_fresh=True,
            direction="",
            trend_status="bearish",
            current_bias="bearish",
        )
        assert result.direction == "sell"

    def test_never_auto_executes(self):
        """Safety invariant: StrategyAgent never returns an 'execute' action."""
        agent = StrategyAgent()
        for state in ["approved_for_demo_auto", "approved_for_manual", "demo_testing"]:
            result = agent.propose_signal(
                context="test",
                symbol="EURUSD",
                direction="buy",
                strategy_id="test",
                lifecycle_state=state,
                quality_score=0.9,
                market_data_fresh=True,
                confidence=0.8,
            )
            assert "review" in result.next_action.lower() or "governance" in result.next_action.lower(), (
                f"StrategyAgent must always require review, got: {result.next_action}"
            )


# ─── SignalReviewerAgent Tests ─────────────────────────────────────────────────


class TestSignalReviewerAgent:
    """Test SignalReviewerAgent domain logic."""

    def test_agent_name(self):
        agent = SignalReviewerAgent()
        assert agent.name == "Signal Reviewer"

    def test_handle_returns_agent_message(self):
        agent = SignalReviewerAgent()
        msg = AgentMessage(
            sender="Orchestrator Agent",
            role="task_dispatch",
            summary="Review signal for EURUSD buy",
            confidence=0.5,
            risk_status="unknown",
        )
        result = agent.handle(msg)
        assert isinstance(result, AgentMessage)
        assert result.sender == "Signal Reviewer"
        assert result.role == "signal_review"

    def test_blocked_signal_status_rejected(self):
        agent = SignalReviewerAgent()
        for status in ["blocked", "stale", "no_signal", "expired", "cancelled"]:
            result = agent.review_signal(
                context="test",
                signal_status=status,
                direction="buy",
                symbol="EURUSD",
            )
            assert result.review_status == "rejected", f"Status '{status}' should be rejected"

    def test_invalid_direction_rejected(self):
        agent = SignalReviewerAgent()
        result = agent.review_signal(
            context="test",
            signal_status="active",
            direction="hold",
            symbol="EURUSD",
        )
        assert result.review_status == "rejected"
        assert any("invalid_direction" in g for g in result.governance_flags)

    def test_governance_blocked_lifecycle_rejects(self):
        agent = SignalReviewerAgent()
        for state in ["draft", "pending_review", "rejected", "deprecated", "suspended"]:
            result = agent.review_signal(
                context="test",
                signal_status="active",
                direction="buy",
                symbol="EURUSD",
                strategy_lifecycle_state=state,
            )
            assert result.review_status == "rejected", (
                f"Lifecycle state '{state}' should cause rejection"
            )

    def test_news_halt_flags_risk(self):
        agent = SignalReviewerAgent()
        result = agent.review_signal(
            context="test",
            signal_status="active",
            direction="buy",
            symbol="EURUSD",
            strategy_lifecycle_state="approved_for_demo_auto",
            news_halt_active=True,
            quality_score=0.8,
        )
        assert result.review_status == "requires_risk_review"
        assert "news_halt_active" in result.risk_flags

    def test_stale_market_data_flags_risk(self):
        agent = SignalReviewerAgent()
        result = agent.review_signal(
            context="test",
            signal_status="active",
            direction="buy",
            symbol="EURUSD",
            strategy_lifecycle_state="approved_for_demo_auto",
            market_data_fresh=False,
            quality_score=0.8,
        )
        assert result.review_status == "requires_risk_review"
        assert "stale_market_data" in result.risk_flags

    def test_excessive_spread_flags_risk(self):
        agent = SignalReviewerAgent()
        result = agent.review_signal(
            context="test",
            signal_status="active",
            direction="buy",
            symbol="EURUSD",
            strategy_lifecycle_state="approved_for_demo_auto",
            spread_points=50.0,
            max_spread_points=30.0,
            quality_score=0.8,
        )
        assert result.review_status == "requires_risk_review"
        assert any("excessive_spread" in r for r in result.risk_flags)

    def test_duplicate_signal_flags_risk(self):
        agent = SignalReviewerAgent()
        result = agent.review_signal(
            context="test",
            signal_status="active",
            direction="buy",
            symbol="EURUSD",
            strategy_lifecycle_state="approved_for_demo_auto",
            duplicate_signal=True,
            quality_score=0.8,
        )
        assert result.review_status == "requires_risk_review"
        assert "duplicate_signal" in result.risk_flags

    def test_correlation_conflict_flags_risk(self):
        agent = SignalReviewerAgent()
        result = agent.review_signal(
            context="test",
            signal_status="active",
            direction="buy",
            symbol="EURUSD",
            strategy_lifecycle_state="approved_for_demo_auto",
            correlation_conflict=True,
            quality_score=0.8,
        )
        assert result.review_status == "requires_risk_review"
        assert "correlation_conflict" in result.risk_flags

    def test_low_confidence_flags_risk(self):
        agent = SignalReviewerAgent()
        result = agent.review_signal(
            context="test",
            signal_status="active",
            direction="buy",
            symbol="EURUSD",
            strategy_lifecycle_state="approved_for_demo_auto",
            confidence=0.2,
            min_confidence=0.4,
            quality_score=0.8,
        )
        assert result.review_status == "requires_risk_review"
        assert any("low_confidence" in r for r in result.risk_flags)

    def test_clean_signal_approved_for_review(self):
        agent = SignalReviewerAgent()
        result = agent.review_signal(
            context="test",
            signal_status="active",
            direction="buy",
            symbol="EURUSD",
            strategy_id="trend_pullback_v1",
            strategy_lifecycle_state="approved_for_demo_auto",
            confidence=0.7,
            quality_score=0.8,
            market_data_fresh=True,
            spread_points=5.0,
            max_spread_points=30.0,
        )
        assert result.review_status == "approved_for_review"
        assert len(result.risk_flags) == 0
        assert len(result.governance_flags) == 0
        # Even approved_for_review does NOT authorize execution
        assert "Execution Guard" in result.next_action

    def test_never_approves_execution(self):
        """Safety invariant: SignalReviewerAgent never returns 'approved_for_execution'."""
        agent = SignalReviewerAgent()
        result = agent.review_signal(
            context="test",
            signal_status="active",
            direction="buy",
            symbol="EURUSD",
            strategy_lifecycle_state="approved_for_demo_auto",
            confidence=1.0,
            quality_score=1.0,
            market_data_fresh=True,
        )
        assert result.review_status != "approved_for_execution"
        assert "execution" not in result.review_status.lower() or "no_execution" in result.review_status.lower()

    def test_sell_direction_accepted(self):
        agent = SignalReviewerAgent()
        result = agent.review_signal(
            context="test",
            signal_status="active",
            direction="sell",
            symbol="GBPUSD",
            strategy_lifecycle_state="approved_for_demo_auto",
            confidence=0.6,
            quality_score=0.7,
        )
        assert result.review_status == "approved_for_review"
        assert "sell" in result.summary.lower()

    def test_multiple_risk_flags(self):
        agent = SignalReviewerAgent()
        result = agent.review_signal(
            context="test",
            signal_status="active",
            direction="buy",
            symbol="EURUSD",
            strategy_lifecycle_state="approved_for_demo_auto",
            news_halt_active=True,
            duplicate_signal=True,
            correlation_conflict=True,
            spread_points=50.0,
            max_spread_points=30.0,
            quality_score=0.8,
        )
        assert result.review_status == "requires_risk_review"
        assert len(result.risk_flags) >= 3


# ─── Integration: Agent Pipeline Safety ────────────────────────────────────────


class TestAgentPipelineSafety:
    """Verify the full agent pipeline maintains safety invariants."""

    def test_pipeline_never_auto_executes(self):
        """End-to-end: Strategy → Reviewer → Risk Manager never auto-executes."""
        strategy_agent = StrategyAgent()
        reviewer = SignalReviewerAgent()
        risk_agent = RiskManagerAgent()

        # Step 1: Strategy proposes a signal
        proposal = strategy_agent.propose_signal(
            context="EURUSD bullish trend",
            symbol="EURUSD",
            direction="buy",
            strategy_id="trend_pullback_v1",
            timeframe="M1",
            lifecycle_state="approved_for_demo_auto",
            quality_score=0.8,
            market_data_fresh=True,
            trend_status="bullish",
            current_bias="bullish",
            confidence=0.7,
        )
        assert proposal.governance_status == "proposal_ready_for_review"

        # Step 2: Signal Reviewer reviews
        review = reviewer.review_signal(
            context=proposal.summary,
            signal_status="active",
            direction=proposal.direction,
            symbol=proposal.symbol,
            strategy_id=proposal.strategy_id,
            strategy_lifecycle_state=proposal.lifecycle_state,
            confidence=proposal.confidence,
            quality_score=0.8,
            market_data_fresh=True,
        )
        assert review.review_status in {"approved_for_review", "requires_risk_review"}

        # Step 3: Risk Manager evaluates
        risk = risk_agent.evaluate_risk(
            context=review.summary,
            trading_mode="monitor_only",  # Default safe mode
        )
        # Even with clean signal, monitor_only blocks execution
        assert risk.risk_status == "risk_blocked"
        assert "Execution Guard" in risk.next_action or "monitor_only" in str(risk.blockers)

    def test_pipeline_with_demo_auto_still_requires_guard(self):
        """Even with demo_auto mode, the pipeline requires Execution Guard."""
        strategy_agent = StrategyAgent()
        reviewer = SignalReviewerAgent()
        risk_agent = RiskManagerAgent()

        proposal = strategy_agent.propose_signal(
            context="EURUSD bullish trend",
            symbol="EURUSD",
            direction="buy",
            strategy_id="trend_pullback_v1",
            timeframe="M1",
            lifecycle_state="approved_for_demo_auto",
            quality_score=0.8,
            market_data_fresh=True,
            confidence=0.7,
        )

        review = reviewer.review_signal(
            context=proposal.summary,
            signal_status="active",
            direction=proposal.direction,
            symbol=proposal.symbol,
            strategy_id=proposal.strategy_id,
            strategy_lifecycle_state=proposal.lifecycle_state,
            confidence=proposal.confidence,
            quality_score=0.8,
        )

        risk = risk_agent.evaluate_risk(
            context=review.summary,
            trading_mode="demo_auto",
            daily_loss_pct=1.0,
            max_daily_loss_pct=5.0,
            weekly_loss_pct=3.0,
            max_weekly_loss_pct=10.0,
            open_trades=1,
            max_open_trades=3,
        )

        # Risk conditions may be acceptable, but the agent still doesn't authorize execution
        assert "Execution Guard" in risk.next_action
        assert "approved" not in risk.risk_status or risk.risk_status == "risk_conditions_acceptable"