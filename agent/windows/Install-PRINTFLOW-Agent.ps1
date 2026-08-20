$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$configDirectory = Join-Path $root "config"
$configPath = Join-Path $configDirectory "agent-config.json"
$launcher = Join-Path $root "Start-PRINTFLOW-Agent.ps1"

Write-Host "Configuracao segura do PRINTFLOW Agent"
$token = Read-Host "Digite ou cole o Token do Agent" -AsSecureString
$encryptedToken = $token | ConvertFrom-SecureString
$network = Read-Host "Rede adicional em CIDR ou ENTER para descoberta automatica"

New-Item -ItemType Directory -Force -Path $configDirectory | Out-Null
@{
    encrypted_token = $encryptedToken
    extra_network = $network.Trim()
    configured_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8

$taskName = "PRINTFLOW Agent"
$powerShell = (Get-Command powershell.exe).Source
$arguments = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$launcher`" -Daemon"
$action = New-ScheduledTaskAction -Execute $powerShell -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Monitoramento PRINTFLOW" -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "PRINTFLOW Agent instalado e iniciado com sucesso." -ForegroundColor Green
