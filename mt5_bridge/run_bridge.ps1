$ErrorActionPreference = "Stop"
$env:BRIDGE_MODE = if ($env:BRIDGE_MODE) { $env:BRIDGE_MODE } else { "demo" }
$env:ALLOW_LIVE_TRADING = if ($env:ALLOW_LIVE_TRADING) { $env:ALLOW_LIVE_TRADING } else { "false" }
.\.venv\Scripts\python -m uvicorn bridge_service:app --host 0.0.0.0 --port 8501
