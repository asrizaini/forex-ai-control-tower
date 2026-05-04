# Unattended Reboot Persistent Secrets

This flow removes dependency on volatile runtime environment variables. Services will read root-only Linux environment files and Windows machine-level environment variables after reboot.

## One-Time Paste Form

1. Copy the template:

```powershell
Set-Location E:\codex\fx-ai-tower\forex-ai-control-tower
New-Item -ItemType Directory -Force secrets | Out-Null
Copy-Item docs\control_tower_credentials.env.template secrets\control_tower_credentials.env
notepad secrets\control_tower_credentials.env
```

2. Paste/fill all values in `secrets\control_tower_credentials.env`.

3. Do not commit or screenshot the filled file.

## Optional Local Vault Encryption

The easiest safe keeper is Ansible Vault encryption for the local paste form. The deployment playbook can decrypt it when you provide the vault password file.

```powershell
Set-Location E:\codex\fx-ai-tower\forex-ai-control-tower
New-Item -ItemType Directory -Force secrets | Out-Null

# Put a long random vault password in this ignored file.
notepad secrets\ansible-vault-password.txt

docker compose --env-file secrets\control_tower_credentials.env `
  -f docker/controller-runner.compose.yml run --rm controller `
  ansible-vault encrypt secrets/control_tower_credentials.env `
  --vault-password-file secrets/ansible-vault-password.txt
```

After encryption, keep both files in `secrets/`. They remain ignored by Git.

## Deploy Persistent Secrets

For plaintext local paste form:

```powershell
.\scripts\deploy_persistent_secrets.ps1
```

For Ansible Vault encrypted paste form:

```powershell
.\scripts\deploy_persistent_secrets.ps1 -VaultPasswordFile secrets\ansible-vault-password.txt
```

The playbook installs only application runtime keys to the remote services. Deployment-only values such as GitHub token and SSH passwords are not copied into app runtime files.

## Installed Locations

Linux control node:

- `/etc/forex-ai-control-tower/runtime.env`
- Owner: `root`
- Mode: `0600`

Linux worker nodes:

- `/etc/forex-ai-control-tower/runtime.env`
- Owner: `root`
- Mode: `0600`

Windows MT5 bridge:

- Required bridge variables are set as Machine-level environment variables.

## Verify

```powershell
Invoke-RestMethod "http://10.10.1.81:8000/health"
Invoke-RestMethod "http://10.10.1.81:8000/api/v1/news/status?symbol=EURUSD"
Invoke-RestMethod "http://10.10.1.81:8000/api/v1/notifications/channels/status"
Invoke-RestMethod "http://10.10.1.86:8501/health" -Headers @{ "X-Bridge-Token" = "<do not paste token here; use your local variable>" }
```

## Security Notes

- The filled paste form must stay under `secrets/`.
- Prefer encrypting it with Ansible Vault.
- Do not include broker passwords until a dedicated encrypted broker credential workflow is approved.
- After deployment, normal server reboot no longer depends on the controller environment variables.
