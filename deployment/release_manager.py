from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass(frozen=True)
class DeploymentRecord:
    deployment_id: str
    version: str
    environment: str
    changelog: str
    backup_point: str
    test_result: str
    approver: str
    rollback_command: str
    created_at: str


def deployment_record(
    version: str,
    approver: str,
    changelog: str,
    backup_point: str,
    rollback_command: str,
    environment: str = "staging",
    test_result: str = "not_run",
) -> dict:
    record = DeploymentRecord(
        deployment_id=f"dep_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
        version=version,
        environment=environment,
        changelog=changelog,
        backup_point=backup_point,
        test_result=test_result,
        approver=approver,
        rollback_command=rollback_command,
        created_at=datetime.utcnow().isoformat() + "Z",
    )
    return {**asdict(record), "rollback_available": bool(rollback_command)}
