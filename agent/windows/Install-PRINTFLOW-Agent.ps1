$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$configDirectory = Join-Path $root "config"
$configPath = Join-Path $configDirectory "agent-config.json"
$launcher = Join-Path $root "Start-PRINTFLOW-Agent.ps1"

Write-Host "Configuracao segura do PRINTFLOW Agent"
Write-Host "Copie o Token do Agent para a area de transferencia."
Read-Host "Depois pressione ENTER para continuar"
$plainToken = [string](Get-Clipboard -Raw)
$plainToken = $plainToken.Trim()
if ($plainToken -notmatch '^[A-Za-z0-9_-]{40,100}$') {
    throw "Token invalido. Copie o token completo do Dashboard e execute novamente."
}

$validationBody = @{
    agent_token = $plainToken
    agent_name = "PRINTFLOW Agent Windows Installer"
    agent_version = "0.2.2"
    status = "starting"
} | ConvertTo-Json
try {
    Invoke-RestMethod `
        -Uri "https://printflow-api-genesis.onrender.com/api/v1/printers/agent/heartbeat" `
        -Method Post `
        -ContentType "application/json" `
        -Body $validationBody | Out-Null
}
catch {
    throw "Token recusado pela API. Copie o token atual do Dashboard e tente novamente."
}
$validationBody = $null

$token = ConvertTo-SecureString $plainToken -AsPlainText -Force
$encryptedToken = $token | ConvertFrom-SecureString
$plainToken = $null
Set-Clipboard -Value "[PRINTFLOW token protegido]"
$network = Read-Host "Rede adicional em CIDR ou ENTER para descoberta automatica"

New-Item -ItemType Directory -Force -Path $configDirectory | Out-Null
@{
    encrypted_token = $encryptedToken
    extra_network = $network.Trim()
    configured_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8

$taskName = "PRINTFLOW Agent"
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
Get-Process -Name "PRINTFLOW-Agent" -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue

$powerShell = (Get-Command powershell.exe).Source
$arguments = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$launcher`" -Daemon"
$action = New-ScheduledTaskAction -Execute $powerShell -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Monitoramento PRINTFLOW" -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "PRINTFLOW Agent instalado e iniciado com sucesso." -ForegroundColor Green
