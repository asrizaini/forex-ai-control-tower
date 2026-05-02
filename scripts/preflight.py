from __future__ import annotations

import argparse
import os
import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    hostname: str
    ip: str
    ports: tuple[int, ...]


TARGETS = (
    Target("fx-control", "10.10.1.81", (22,)),
    Target("fx-llm-local-reason", "10.10.1.82", (22,)),
    Target("fx-llm-local-code", "10.10.1.83", (22,)),
    Target("fx-market-worker", "10.10.1.84", (22,)),
    Target("fx-strategy-risk-worker", "10.10.1.85", (22,)),
    Target("fx-mt5-bridge", "10.10.1.86", (22, 5985)),
)


def port_open(ip: str, port: int, timeout: float = 1.0) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((ip, port)) == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    required_env = [
        "GITHUB_OWNER",
        "GITHUB_REPO",
        "GITHUB_TOKEN",
        "LINUX_STANDARD_SSH_PASSWORD",
        "LINUX_STANDARD_SUDO_PASSWORD",
        "WINDOWS_MT5_USER",
        "WINDOWS_MT5_PASSWORD",
        "WINDOWS_MT5_SSH_PASSWORD",
    ]
    print("Deployment preflight")
    print(f"dry_run={args.dry_run}")
    for name in required_env:
        print(f"env {name}: {'present' if os.getenv(name) else 'missing'}")
    for target in TARGETS:
        for port in target.ports:
            print(f"{target.hostname} {target.ip}:{port} open={port_open(target.ip, port)}")


if __name__ == "__main__":
    main()
