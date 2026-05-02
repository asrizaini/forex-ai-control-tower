from dataclasses import dataclass


@dataclass(frozen=True)
class AgentMessage:
    sender: str
    role: str
    summary: str
    confidence: float = 0.0
    risk_status: str = "unknown"


class BaseAgent:
    name = "Base Agent"

    def handle(self, message: AgentMessage) -> AgentMessage:
        return AgentMessage(sender=self.name, role="response", summary=f"Received: {message.summary}")
