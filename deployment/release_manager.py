def deployment_record(version: str, approver: str) -> dict:
    return {"version": version, "approver": approver, "rollback_available": True}
