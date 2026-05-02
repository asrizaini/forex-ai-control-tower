# Windows MT5 Bridge

This bridge is safe by default and starts in demo mode. It never stores broker credentials.

Setup:

```powershell
.\setup_venv.ps1
.\run_bridge.ps1
```

Live trading requires `ALLOW_LIVE_TRADING=true`, production governance approval, `order_check`, and a valid Execution Guard token.
