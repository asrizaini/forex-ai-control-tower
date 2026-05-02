from __future__ import annotations

from .event_schema import AgentTheaterEvent


def format_event(event: AgentTheaterEvent, language: str = "en") -> dict:
    label = "Ringkasan" if language == "ms-MY" else "Summary"
    return {
        "agent": event.agent,
        "label": label,
        "summary": event.summary,
        "input_sources": event.input_sources,
        "result": event.result,
        "confidence": event.confidence,
        "risk_status": event.risk_status,
        "next_action": event.next_action,
        "contains_hidden_chain_of_thought": False,
    }
