$ErrorActionPreference = "Stop"
New-NetFirewallRule -DisplayName "Forex AI MT5 Bridge 8501" -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow -ErrorAction SilentlyContinue
