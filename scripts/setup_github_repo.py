from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


def run(command: list[str], cwd: Path, sensitive: bool = False, env: dict[str, str] | None = None) -> None:
    printable = " ".join(command)
    print("+ [sensitive command redacted]" if sensitive else f"+ {printable}")
    try:
        subprocess.run(command, cwd=cwd, check=True, env=env)
    except subprocess.CalledProcessError as exc:
        if sensitive:
            raise SystemExit(f"Sensitive command failed with exit code {exc.returncode}") from None
        raise


def write_git_askpass() -> Path:
    script = Path(tempfile.gettempdir()) / "forex_ai_git_askpass.cmd"
    script.write_text(
        "@echo off\n"
        "echo %* | findstr /I \"Username\" >nul\n"
        "if %errorlevel%==0 (\n"
        "  echo x-access-token\n"
        ") else (\n"
        "  echo %GITHUB_TOKEN%\n"
        ")\n",
        encoding="utf-8",
    )
    return script


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def create_remote(owner: str, repo: str, token: str) -> None:
    login_request = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(login_request, timeout=30) as response:
            login = json.loads(response.read().decode())["login"]
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise SystemExit("GitHub authentication failed. Check GITHUB_TOKEN and rotate it if there is any doubt.") from None
        if exc.code == 403:
            raise SystemExit("GitHub token is authenticated but not authorized for this operation.") from None
        raise SystemExit(f"GitHub authentication check failed with HTTP {exc.code}.") from None
    url = "https://api.github.com/user/repos" if owner == login else f"https://api.github.com/orgs/{owner}/repos"
    payload = json.dumps({"name": repo, "private": True, "auto_init": False}).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"GitHub repo create status: {response.status}")
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            print("GitHub repo already exists or cannot be created with current owner/token.")
            return
        if exc.code == 401:
            raise SystemExit("GitHub authentication failed while creating the repo.") from None
        if exc.code == 403:
            raise SystemExit("GitHub token is not authorized to create repos for this owner.") from None
        raise SystemExit(f"GitHub repo creation failed with HTTP {exc.code}.") from None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init-local", action="store_true")
    parser.add_argument("--create-remote", action="store_true")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    owner = require_env("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO", "forex-ai-control-tower")
    token = require_env("GITHUB_TOKEN")

    if args.init_local and not (root / ".git").exists():
        run(["git", "init"], root)
        if not subprocess.run(["git", "config", "user.email"], cwd=root).stdout:
            run(["git", "config", "user.email", "forex-ai-control-tower@example.local"], root)
        if not subprocess.run(["git", "config", "user.name"], cwd=root).stdout:
            run(["git", "config", "user.name", "Forex AI Control Tower"], root)

    if args.create_remote:
        create_remote(owner, repo, token)

    remote = f"https://github.com/{owner}/{repo}.git"
    existing = subprocess.run(["git", "remote"], cwd=root, capture_output=True, text=True, check=False).stdout
    if "origin" not in existing.split():
        run(["git", "remote", "add", "origin", remote], root)

    if args.push:
        run(["git", "add", "."], root)
        staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=root, capture_output=True, text=True, check=True).stdout
        forbidden = [line for line in staged.splitlines() if line == ".env" or line.endswith(".env")]
        if forbidden:
            raise SystemExit("Refusing to commit env files: " + ", ".join(forbidden))
        if staged.strip():
            run(["git", "commit", "-m", "Initial secure scaffold"], root)
        else:
            print("No local changes to commit.")
        run(["git", "branch", "-M", "main"], root)
        run(
            ["git", "push", "-u", "origin", "main"],
            root,
            sensitive=True,
            env={
                **os.environ,
                "GITHUB_TOKEN": token,
                "GIT_ASKPASS": str(write_git_askpass()),
                "GIT_TERMINAL_PROMPT": "0",
            },
        )


if __name__ == "__main__":
    main()
