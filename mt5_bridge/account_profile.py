from dataclasses import dataclass


@dataclass(frozen=True)
class AccountProfile:
    account_id: str
    terminal_port: int
    environment: str = "demo"
    trading_mode: str = "monitor_only"
