$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()

$currentPrincipal = [Security.Principal.WindowsPrincipal]::new(
    $currentIdentity
)

$isAdministrator = $currentPrincipal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (-not $isAdministrator) {

    $scriptPath = $MyInvocation.MyCommand.Path

    Start-Process powershell.exe `
        -Verb RunAs `
        -ArgumentList `
        "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

    exit
}

$ErrorActionPreference = "Stop"

$taskName = "PRINTFLOW Agent"
$watchdogTaskName = "PRINTFLOW Agent Watchdog"

$installRoot = Join-Path `
    $env:ProgramData `
    "PRINTFLOW\Agent"

$watchdogTask = Get-ScheduledTask `
    -TaskName $watchdogTaskName `
    -ErrorAction SilentlyContinue

if ($watchdogTask) {
    Stop-ScheduledTask `
        -TaskName $watchdogTaskName `
        -ErrorAction SilentlyContinue

    Unregister-ScheduledTask `
        -TaskName $watchdogTaskName `
        -Confirm:$false
}

$task = Get-ScheduledTask `
    -TaskName $taskName `
    -ErrorAction SilentlyContinue

if ($task) {

    Stop-ScheduledTask `
        -TaskName $taskName `
        -ErrorAction SilentlyContinue

    Unregister-ScheduledTask `
        -TaskName $taskName `
        -Confirm:$false
}

Get-CimInstance `
    Win32_Process `
    -Filter "Name='PRINTFLOW-Agent.exe'" `
    -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -and
        $_.ExecutablePath.StartsWith(
            $installRoot,
            [StringComparison]::OrdinalIgnoreCase
        )
    } |
    ForEach-Object {

        Stop-Process `
            -Id $_.ProcessId `
            -Force `
            -ErrorAction SilentlyContinue
    }

$configPath = Join-Path `
    $installRoot `
    "config\agent-config.json"

if (Test-Path $configPath) {

    Remove-Item `
        -LiteralPath $configPath `
        -Force `
        -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Tarefa automatica removida." -ForegroundColor Green
Write-Host "Processo residente encerrado." -ForegroundColor Green
Write-Host "Token protegido removido." -ForegroundColor Green
Write-Host ""
Write-Host "Logs e inventario foram preservados em:"
Write-Host $installRoot