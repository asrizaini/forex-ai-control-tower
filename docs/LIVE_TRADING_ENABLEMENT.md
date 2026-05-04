# Live Trading Enablement

Live trading is intentionally gated. The system must not be switched live by editing random environment variables or restarting services manually.

## Required Gates

The readiness endpoint must show no blocking gates:

```text
http://10.10.1.81:8000/api/v1/system/production-readiness
```

Required gates include:

- security review completed
- broker compatibility passed
- market data quality passed
- kill switch tested
- explicit production-live approval recorded

## Enable Command

Set this environment variable only after the operator has approved live mode:

```powershell
Set-Item -Path Env:LIVE_TRADING_EXPLICIT_CONFIRMATION -Value '<exact production-live approval phrase from the pre-live approval page>'
```

Then run:

```powershell
docker compose -f docker/controller-runner.compose.yml run --rm controller ansible-playbook -i ansible/inventory.yml ansible/playbooks/live_trading_enable.yml
```

The playbook refuses to continue if any readiness gate is still blocking.

## Emergency Disable

```powershell
docker compose -f docker/controller-runner.compose.yml run --rm controller ansible-playbook -i ansible/inventory.yml ansible/playbooks/live_trading_disable.yml
```

This disables live runtime flags on the control API and Windows MT5 bridge.

## Safety Notes

- Laravel is only an operator console.
- FastAPI remains the source of truth for approvals, audit, and Execution Guard.
- MT5 bridge still requires `order_check` before `order_send`.
- MT5 bridge still requires a valid Execution Guard token.
- Live trading is not enabled unless both control API and MT5 bridge runtime flags are true and all gates pass.
