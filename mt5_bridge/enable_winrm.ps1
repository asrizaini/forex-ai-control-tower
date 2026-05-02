$ErrorActionPreference = "Stop"
Enable-PSRemoting -Force
winrm set winrm/config/service/auth '@{Basic="false"}'
winrm set winrm/config/service '@{AllowUnencrypted="false"}'
