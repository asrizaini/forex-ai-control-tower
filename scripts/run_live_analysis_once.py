from __future__ import annotations

import os
from types import SimpleNamespace


def _load_process_environment() -> None:
    pid = os.getenv("CONTROL_API_PID")
    if not pid:
        return
    try:
        raw_items = open(f"/proc/{pid}/environ", "rb").read().split(b"\0")
    except OSError:
        return
    for item in raw_items:
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        os.environ[key.decode("utf-8", errors="ignore")] = value.decode("utf-8", errors="ignore")


def main() -> None:
    _load_process_environment()
    from control.api.db import SessionLocal, init_db
    from control.api.routes.trading import run_analysis

    init_db()
    db = SessionLocal()
    try:
        result = run_analysis(db=db, principal=SimpleNamespace(role="super_admin", user_id="operator_approved"))
        print({"status": result["status"], "pairs_processed": result["pairs_processed"]})
    finally:
        db.close()


if __name__ == "__main__":
    main()
