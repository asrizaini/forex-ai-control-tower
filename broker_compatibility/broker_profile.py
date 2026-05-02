from dataclasses import dataclass

@dataclass(frozen=True)
class BrokerProfile:
    name: str
    symbols: tuple[str, ...]
