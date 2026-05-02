from .account_profile import AccountProfile


def default_terminal_profiles(count: int = 4) -> list[AccountProfile]:
    return [AccountProfile(account_id=f"account-{i}", terminal_port=8500 + i) for i in range(1, count + 1)]
