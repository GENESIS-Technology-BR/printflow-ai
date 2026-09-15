$ErrorActionPreference = "Stop"

$sourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$installRoot = Join-Path $env:ProgramData "PRINTFLOW\Agent"
$sourceWatchdog = Join-Path $sourceRoot "Watchdog-PRINTFLOW-Agent.ps1"
$installedWatchdog = Join-Path $installRoot "Watchdog-PRINTFLOW-Agent.ps1"
$watchdogTaskName = "PRINTFLOW Agent Watchdog"

if (-not (Test-Path -LiteralPath $sourceWatchdog)) {
    throw "Watchdog-PRINTFLOW-Agent.ps1 nao encontrado no pacote."
}

if (-not (Test-Path -LiteralPath $installRoot)) {
    throw "Instalacao PRINTFLOW nao encontrada em ProgramData."
}

Copy-Item -LiteralPath $sourceWatchdog -Destination $installedWatchdog -Force

$powerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$action = New-ScheduledTaskAction `
    -Execute $powerShell `
    -Argument ("-NoLogo -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$installedWatchdog`"") `
    -WorkingDirectory $installRoot

$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 5)

$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

$existing = Get-ScheduledTask -TaskName $watchdogTaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $watchdogTaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $watchdogTaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "PRINTFLOW Agent watchdog - health check a cada 5 minutos" `
    -Force | Out-Null

Write-Host "[OK] Watchdog v0.97 sincronizado; verificacao a cada 5 minutos." -ForegroundColor Green
