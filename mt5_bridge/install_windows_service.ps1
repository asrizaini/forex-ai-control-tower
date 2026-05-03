$ErrorActionPreference = "Stop"
$ServiceName = "ForexAI-MT5-Bridge"
$InstallRoot = $env:FOREX_AI_MT5_ROOT
if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = "C:\ForexAI"
}
$RunScript = Join-Path $InstallRoot "mt5_bridge\run_bridge.ps1"
if (-not (Test-Path $RunScript)) {
    $RunScript = Join-Path $PSScriptRoot "run_bridge.ps1"
}
if (-not (Test-Path $RunScript)) {
    throw "run_bridge.ps1 not found. Set FOREX_AI_MT5_ROOT or run this script from mt5_bridge."
}

$PowerShell = (Get-Command powershell.exe).Source
$BinaryPath = "`"$PowerShell`" -NoProfile -ExecutionPolicy Bypass -File `"$RunScript`""

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service -Name $ServiceName -ErrorAction SilentlyContinue
    sc.exe delete $ServiceName | Out-Null
    Start-Sleep -Seconds 2
}

New-Service `
    -Name $ServiceName `
    -BinaryPathName $BinaryPath `
    -DisplayName "Forex AI MT5 Bridge" `
    -Description "FastAPI MT5 bridge. Secrets are read from machine/user environment only." `
    -StartupType Automatic | Out-Null

Write-Host "Installed $ServiceName as an automatic Windows service."
Write-Host "No secrets were stored by this script. Configure BRIDGE_API_TOKEN and EXECUTION_GUARD_SIGNING_KEY as environment variables only."
