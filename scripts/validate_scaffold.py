from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED = [
    ".gitignore",
    "ansible/inventory.ini.example",
    "docker/controller-runner.Dockerfile",
    "control/api/main.py",
    "mt5_bridge/bridge_service.py",
    "execution_guard/guard.py",
    "locales/en/common.json",
    "locales/ms-MY/common.json",
    "agent_theater/formatter.py",
    "openclaw_gateway/allowed_actions.yaml",
    "mobile/android_api_contract.md",
    "deployment/final_deployment_report_template.md",
]

SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9_]+"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)(password|token|api_key)\s*=\s*['\"][^<$][^'\"]{8,}['\"]"),
]

SKIP_DIRS = {".git", "node_modules", "dist", "build", "__pycache__", ".pytest_cache", ".venv"}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED if not (root / path).exists()]
    if missing:
        print("Missing required files:", missing)
        return 1
    bad = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix not in {".png", ".jpg", ".ico"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    bad.append(str(path.relative_to(root)))
    if bad:
        print("Potential secret patterns found:", bad)
        return 1
    print("Scaffold validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
