param(
    [string]$CredentialsFile = "secrets\control_tower_credentials.env"
)

$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$composeArgs = @("compose")
if (Test-Path $CredentialsFile) {
    $composeArgs += @("--env-file", $CredentialsFile)
}
$composeArgs += @(
    "-f", "docker/controller-runner.compose.yml",
    "run", "--rm", "controller",
    "ansible-playbook", "-i", "ansible/inventory.yml", "ansible/playbooks/timezone.yml"
)

docker @composeArgs
