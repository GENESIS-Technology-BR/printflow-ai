$ErrorActionPreference = "Stop"

$taskName = "TALVOA Agent"
$installRoot = Join-Path $env:ProgramData "TALVOA\Agent"
$logPath = Join-Path $installRoot "logs\watchdog.log"
$healthPath = Join-Path $installRoot "output\agent_health.json"
$staleMinutes = 12

function Get-TALVOAProcess {
    Get-CimInstance Win32_Process -Filter "Name='TALVOA-Agent.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($installRoot,[StringComparison]::OrdinalIgnoreCase) } |
        Select-Object -First 1
}

function Restart-TALVOAAgent([string]$reason) {
    $process = Get-TALVOAProcess
    if ($process) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }

    Start-ScheduledTask -TaskName $taskName
    Start-Sleep -Seconds 3

    $recovered = Get-TALVOAProcess
    if (-not $recovered) {
        throw "Auto-Recovery executado, mas o processo nao voltou. Motivo=$reason"
    }

    return "$(Get-Date -Format o) | RECOVERY | $reason | PID=$($recovered.ProcessId)"
}

try {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $task) { throw "Tarefa TALVOA Agent nao encontrada." }

    $process = Get-TALVOAProcess

    if (-not $process) {
        $message = Restart-TALVOAAgent "Processo ausente"
    }
    elseif (-not (Test-Path -LiteralPath $healthPath)) {
        # Na primeira inicializacao o health ainda pode nao existir.
        # Nao reinicia um processo vivo somente pela ausencia inicial do arquivo.
        $message = "$(Get-Date -Format o) | WARN | PID=$($process.ProcessId) | agent_health.json ainda nao criado"
    }
    else {
        $health = Get-Content -LiteralPath $healthPath -Raw -ErrorAction Stop | ConvertFrom-Json
        if (-not $health.updated_at) {
            throw "agent_health.json sem updated_at."
        }

        $updatedAt = [DateTimeOffset]::Parse($health.updated_at)
        $age = [DateTimeOffset]::UtcNow - $updatedAt.ToUniversalTime()

        if ($age.TotalMinutes -gt $staleMinutes) {
            $ageText = [Math]::Round($age.TotalMinutes, 1)
            $message = Restart-TALVOAAgent "Health travado ha $ageText min (status=$($health.status))"
        }
        else {
            $ageText = [Math]::Round($age.TotalMinutes, 1)
            $message = "$(Get-Date -Format o) | OK | PID=$($process.ProcessId) | health=$($health.status) | age=$ageText min"
        }
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
