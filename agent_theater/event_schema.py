from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentTheaterEvent:
    agent: str
    summary: str
    input_sources: tuple[str, ...]
    result: str
    confidence: float
    risk_status: str
    next_action: str
