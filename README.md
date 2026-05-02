# Forex AI Control Tower

A secure, expandable, admin-controlled scaffold for a bilingual Forex AI operating system.

Core principle:

**AI analyzes. Risk engine controls. Admin approves. MT5 executes. Everything is logged.**

This first milestone is intentionally safe:

- Default trading mode is `monitor_only`.
- Default execution environment is `demo`.
- Live auto-trading is disabled.
- MT5 order sending requires an Execution Guard approval token.
- The MT5 bridge rejects live trading unless explicitly enabled by environment variables.
- No secrets are committed or hardcoded.

## Controller Quick Start

From the Windows controller:

```powershell
cd E:\codex\fx-ai-tower\forex-ai-control-tower
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python scripts\validate_scaffold.py
.\.venv\Scripts\python scripts\preflight.py --dry-run
```

Build the Dockerized Ansible runner:

```powershell
docker compose -f docker/controller-runner.compose.yml build
docker compose -f docker/controller-runner.compose.yml run --rm controller ansible-playbook --syntax-check -i ansible/inventory.yml ansible/playbooks/site.yml
```

## GitHub Setup

Set these variables in your shell only:

- `GITHUB_OWNER`
- `GITHUB_REPO`
- `GITHUB_TOKEN`

Then run:

```powershell
python scripts\setup_github_repo.py --init-local --create-remote --push
```

The script masks token-derived values in output and never writes the token to disk.

## Deployment Safety

Real deployment is a later phase. Before deploying, provide credentials through environment variables only:

- `LINUX_STANDARD_SSH_PASSWORD`
- `LINUX_STANDARD_SUDO_PASSWORD`
- `WINDOWS_MT5_USER`
- `WINDOWS_MT5_PASSWORD`
- `WINDOWS_MT5_SSH_PASSWORD`

Do not commit generated real inventory files, `.env` files, keys, tokens, or logs.

To deploy after the required environment variables are set:

```powershell
docker compose -f docker/controller-runner.compose.yml run --rm controller ansible-playbook -i ansible/inventory.yml ansible/playbooks/site.yml
```
