$ErrorActionPreference = "Stop"

$taskName = "PRINTFLOW Agent"
$installRoot = Join-Path $env:ProgramData "PRINTFLOW\\Agent"
$logPath = Join-Path $installRoot "logs\\watchdog.log"

try {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $task) { throw "Tarefa PRINTFLOW Agent nao encontrada." }

    $process = Get-CimInstance Win32_Process -Filter "Name='PRINTFLOW-Agent.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($installRoot,[StringComparison]::OrdinalIgnoreCase) } |
        Select-Object -First 1

    if (-not $process) {
        Start-ScheduledTask -TaskName $taskName
        $message = "$(Get-Date -Format o) | RECOVERY | Agent ausente; tarefa reiniciada."
    } else {
        $message = "$(Get-Date -Format o) | OK | PID=$($process.ProcessId)"
    }
}
catch {
    $message = "$(Get-Date -Format o) | ERROR | $($_.Exception.Message)"
}

$logDirectory = Split-Path -Parent $logPath
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
Add-Content -LiteralPath $logPath -Value $message -Encoding UTF8

try {
    $lines = Get-Content -LiteralPath $logPath -ErrorAction Stop
    if ($lines.Count -gt 500) {
        $lines | Select-Object -Last 500 | Set-Content -LiteralPath $logPath -Encoding UTF8
    }
}
catch {}
