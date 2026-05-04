param(
    [string]$CredentialsFile = "secrets\control_tower_credentials.env",
    [string]$VaultPasswordFile = ""
)

$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path $CredentialsFile)) {
    throw "Missing $CredentialsFile. Copy docs\control_tower_credentials.env.template to secrets\control_tower_credentials.env and fill it first."
}

$raw = Get-Content -Raw -Path $CredentialsFile
$required = @(
    "LINUX_STANDARD_SSH_PASSWORD",
    "LINUX_STANDARD_SUDO_PASSWORD",
    "WINDOWS_MT5_USER",
    "WINDOWS_MT5_PASSWORD",
    "POSTGRES_PASSWORD",
    "GRAFANA_ADMIN_PASSWORD",
    "JWT_SECRET_KEY",
    "EXECUTION_GUARD_SIGNING_KEY",
    "BRIDGE_API_TOKEN",
    "NEWS_PROVIDER_API_KEY"
)

foreach ($name in $required) {
    if ($raw -notmatch "(?m)^$([regex]::Escape($name))=(?!\s*$)(?!<)") {
        throw "Missing or placeholder value for $name in $CredentialsFile."
    }
}

$vaultArgs = @()
if ($VaultPasswordFile) {
    if (-not (Test-Path $VaultPasswordFile)) {
        throw "Vault password file not found: $VaultPasswordFile"
    }
    $vaultArgs = @("--vault-password-file", $VaultPasswordFile)
}

docker compose --env-file $CredentialsFile -f docker/controller-runner.compose.yml run --rm controller `
    ansible-playbook -i ansible/inventory.yml ansible/playbooks/persistent_runtime_secrets.yml `
    -e "credentials_file=$($CredentialsFile -replace '\\','/')" @vaultArgs
