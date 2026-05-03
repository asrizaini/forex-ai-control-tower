from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TheaterMode:
    name: str
    purpose: str
    default_agents: tuple[str, ...]
    enabled: bool = True


MODE_CATALOG: tuple[TheaterMode, ...] = (
    TheaterMode(
        "Live Chat View",
        "Real-time human-readable agent status and operator conversation.",
        ("Orchestrator Agent", "Market Data Agent", "Risk Manager", "Execution Agent"),
    ),
    TheaterMode(
        "Workflow Timeline",
        "Ordered view of governed work from signal intake to final safe action.",
        ("Orchestrator Agent", "Signal Reviewer", "Journal Agent", "Audit Logger"),
    ),
    TheaterMode(
        "Debate Mode",
        "Safe visible challenge between strategy, risk, news, and execution perspectives.",
        ("Strategy Agent", "Risk Manager", "News Agent", "Signal Reviewer"),
    ),
    TheaterMode(
        "Boardroom Mode",
        "Executive-ready summary for admin decisions and governance checkpoints.",
        ("Orchestrator Agent", "Governance Center", "Risk Manager", "Security Review Agent"),
    ),
    TheaterMode(
        "Strategy War Room",
        "Strategy research, scoring, validation, and promotion conversation.",
        ("Strategy Agent", "Backtest Agent", "Forward Test Agent", "Strategy Promotion Agent"),
    ),
    TheaterMode(
        "Account Routing Room",
        "Per-account risk, permission, routing, and execution readiness conversation.",
        ("Account Router Agent", "Risk Manager", "Execution Agent", "Broker Compatibility Agent"),
    ),
    TheaterMode(
        "System Improvement Room",
        "Roadmap, deployment, rollback, observability, and upgrade planning conversation.",
        ("System Improvement Agent", "Deployment Agent", "Security Review Agent", "Watchdog Agent"),
    ),
)


def modes_as_dicts() -> list[dict]:
    return [asdict(mode) for mode in MODE_CATALOG]


def mode_names() -> tuple[str, ...]:
    return tuple(mode.name for mode in MODE_CATALOG)
