from __future__ import annotations


def rollback(target: str, dry_run: bool = True) -> dict:
    return {
        "target": target,
        "dry_run": dry_run,
        "status": "planned",
        "requires_backup_verification": True,
        "requires_admin_approval": True,
    }
