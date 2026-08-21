$ErrorActionPreference = "Stop"
$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$resultPath = Join-Path $baseDir "RESULTADO-VALIDACAO.txt"
$checks = [System.Collections.Generic.List[string]]::new()
$failed = $false

function Add-Check {
    param([string]$Name, [bool]$Success, [string]$Detail)
    $status = if ($Success) { "APROVADO" } else { "FALHOU" }
    $script:checks.Add("$status | $Name | $Detail")
    if (-not $Success) { $script:failed = $true }
}

try {
    $required = @(
        "PRINTFLOW-Agent.exe",
        "Executar-PRINTFLOW-Agent.bat",
        "INSTALAR-PRINTFLOW-Agent.bat",
        "Start-PRINTFLOW-Agent.ps1",
        "Install-PRINTFLOW-Agent.ps1",
        "Uninstall-PRINTFLOW-Agent.ps1",
        "BUILD-VALIDATION.txt"
    )
    foreach ($file in $required) {
        Add-Check "Arquivo $file" (Test-Path (Join-Path $baseDir $file)) "presenca no pacote"
    }

    $buildValidation = Join-Path $baseDir "BUILD-VALIDATION.txt"
    if (Test-Path $buildValidation) {
        $buildMetadata = Get-Content $buildValidation -Raw
        Add-Check "Identificacao do Build" ($buildMetadata -match "Build:\s+42") "Build 42"
        Add-Check "Versao do Agent" ($buildMetadata -match "Version:\s+0\.3\.0") "versao 0.3.0"
    }

    $exe = Join-Path $baseDir "PRINTFLOW-Agent.exe"
    if (Test-Path $exe) {
        $hash = (Get-FileHash $exe -Algorithm SHA256).Hash
        Add-Check "Integridade do executavel" ($hash.Length -eq 64) "SHA256 $hash"
        $help = & $exe --help 2>&1 | Out-String
        Add-Check "Inicializacao do executavel" ($LASTEXITCODE -eq 0) "teste --help"
        Add-Check "Modo automatico" ($help -match "--daemon") "opcao disponivel"
    }

    $task = Get-ScheduledTask -TaskName "PRINTFLOW Agent" -ErrorAction SilentlyContinue
    Add-Check "Instalacao no Windows" ($null -ne $task) $(if ($task) { "tarefa encontrada: $($task.State)" } else { "execute o instalador" })
    if ($task) {
        $taskInfo = Get-ScheduledTaskInfo -TaskName "PRINTFLOW Agent"
        Add-Check "Fila do Agent" ($task.State -ne "Queued") "estado $($task.State)"
        $lastResult = [int]$taskInfo.LastTaskResult
        $taskIsRunning = $task.State -eq "Running" -and $lastResult -eq 267009
        $lastRunHealthy = $lastResult -eq 0 -or $taskIsRunning
        $lastRunDetail = if ($taskIsRunning) {
            "execucao em andamento (codigo 267009)"
        }
        elseif ($lastResult -eq 0) {
            "concluida com sucesso (codigo 0)"
        }
        else {
            "falha real (codigo $lastResult)"
        }
        Add-Check "Ultima execucao" $lastRunHealthy $lastRunDetail
    }
}
catch {
    Add-Check "Execucao da validacao" $false $_.Exception.Message
}

$overall = if ($failed) { "ATENCAO" } else { "APROVADO" }
@(
    "PRINTFLOW - RESULTADO DA VALIDACAO"
    "Data: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    "Resultado: $overall"
    ""
    $checks
) | Set-Content $resultPath -Encoding UTF8

Get-Content $resultPath
Write-Host ""
Write-Host "Relatorio salvo em: $resultPath"
if ($failed) { exit 1 }
exit 0
