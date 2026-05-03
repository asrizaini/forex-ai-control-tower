from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class AccountProfile:
    account_id: str
    terminal_port: int
    environment: str = "demo"
    trading_mode: str = "monitor_only"
    terminal_path: str | None = None
    enabled: bool = True


def profile_path() -> Path:
    return Path(os.getenv("MT5_ACCOUNT_PROFILES_FILE", r"C:\ForexAI\mt5_bridge\account_profiles.json"))


def default_account_profiles() -> list[AccountProfile]:
    account_id = os.getenv("MT5_DEFAULT_ACCOUNT_ID", "demo_main")
    port = int(os.getenv("MT5_DEFAULT_BRIDGE_PORT", "8501"))
    terminal_path = os.getenv("MT5_TERMINAL_PATH") or None
    return [AccountProfile(account_id=account_id, terminal_port=port, terminal_path=terminal_path)]


def load_account_profiles(path: Path | None = None) -> list[AccountProfile]:
    target = path or profile_path()
    if not target.exists():
        return default_account_profiles()
    raw = json.loads(target.read_text(encoding="utf-8"))
    return [AccountProfile(**item) for item in raw.get("accounts", []) if item.get("enabled", True)]


def save_account_profiles(profiles: list[AccountProfile], path: Path | None = None) -> Path:
    target = path or profile_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"accounts": [asdict(profile) for profile in profiles]}
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def profile_for_account(account_id: str, path: Path | None = None) -> AccountProfile | None:
    return next((profile for profile in load_account_profiles(path) if profile.account_id == account_id), None)
