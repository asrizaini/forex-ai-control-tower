$ErrorActionPreference = "Stop"
$env:BRIDGE_MODE = if ($env:BRIDGE_MODE) { $env:BRIDGE_MODE } else { "demo" }
$env:ALLOW_LIVE_TRADING = if ($env:ALLOW_LIVE_TRADING) { $env:ALLOW_LIVE_TRADING } else { "false" }
$env:PYTHONPATH = if ($env:PYTHONPATH) { "C:\ForexAI;$env:PYTHONPATH" } else { "C:\ForexAI" }
.\.venv\Scripts\python -m uvicorn bridge_service:app --host 0.0.0.0 --port 8501
