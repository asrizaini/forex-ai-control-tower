from __future__ import annotations

try:
    from .account_profile import AccountProfile, load_account_profiles
except ImportError:
    from account_profile import AccountProfile, load_account_profiles


def default_terminal_profiles(count: int = 4) -> list[AccountProfile]:
    return [AccountProfile(account_id=f"account-{i}", terminal_port=8500 + i) for i in range(1, count + 1)]


def active_terminal_profiles() -> list[AccountProfile]:
    return load_account_profiles()


def account_route_map() -> dict[str, dict]:
    return {
        profile.account_id: {
            "terminal_port": profile.terminal_port,
            "environment": profile.environment,
            "trading_mode": profile.trading_mode,
            "terminal_path_configured": bool(profile.terminal_path),
            "enabled": profile.enabled,
        }
        for profile in active_terminal_profiles()
    }
