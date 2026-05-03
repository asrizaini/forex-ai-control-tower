# Windows MT5 Bridge

This bridge is safe by default and starts in demo mode. It never stores broker credentials.

Setup:

```powershell
.\setup_venv.ps1
.\run_bridge.ps1
```

Live trading requires `ALLOW_LIVE_TRADING=true`, production governance approval, `order_check`, and a valid Execution Guard token.

Optional Windows service mode:

```powershell
.\install_windows_service.ps1
Start-Service ForexAI-MT5-Bridge
```

The service wrapper still reads secrets only from environment variables. The scheduled-task startup path remains the preferred deployment method until the service mode is tested on the target workstation.
