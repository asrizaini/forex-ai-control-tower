from __future__ import annotations


def deploy(dry_run: bool = True, environment: str = "staging") -> dict:
    if environment == "production-live" and dry_run:
        return {"dry_run": True, "environment": environment, "status": "blocked_until_approval_record_exists"}
    return {"dry_run": dry_run, "environment": environment, "status": "planned"}
