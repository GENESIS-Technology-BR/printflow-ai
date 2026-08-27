$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$resultPath = Join-Path $baseDir "RESULTADO-VALIDACAO.txt"

$checks = [System.Collections.Generic.List[string]]::new()
$failed = $false

function Add-Check {
    param(
        [string]$Name,
        [bool]$Success,
        [string]$Detail
    )

    $status = if ($Success) {
        "APROVADO"
    }
    else {
        "FALHOU"
    }

    $script:checks.Add(
        "$status | $Name | $Detail"
    )

    if (-not $Success) {
        $script:failed = $true
    }
}

function Get-MetadataValue {
    param(
        [string]$Text,
        [string]$Name
    )

    $escapedName = [regex]::Escape($Name)

    $match = [regex]::Match(
        $Text,
        "(?m)^${escapedName}:\s*(.+?)\s*$"
    )

    if ($match.Success) {
        return $match.Groups[1].Value.Trim()
    }

    return ""
}

try {

    # ========================================================
    # 1. ARQUIVOS DO PACOTE
    # ========================================================

    $required = @(
        "PRINTFLOW-Agent.exe",
        "Executar-PRINTFLOW-Agent.bat",
        "INSTALAR-PRINTFLOW-Agent.bat",
        "ATUALIZAR-PRINTFLOW-Agent.bat",
        "Start-PRINTFLOW-Agent.ps1",
        "Install-PRINTFLOW-Agent.ps1",
        "Update-PRINTFLOW-Agent.ps1",
        "Uninstall-PRINTFLOW-Agent.ps1",
        "VALIDAR-PRINTFLOW-Build.bat",
        "Validar-PRINTFLOW-Build.ps1",
        "BUILD-VALIDATION.txt",
        "README-TESTE.txt"
    )

    foreach ($file in $required) {

        Add-Check `
            "Arquivo $file" `
            (Test-Path (Join-Path $baseDir $file)) `
            "presenca no pacote"
    }

    # ========================================================
    # 2. METADADOS DINAMICOS DA BUILD
    # ========================================================

    $buildValidation = Join-Path $baseDir "BUILD-VALIDATION.txt"

    $buildNumber = ""
    $buildVersion = ""
    $buildCommit = ""
    $expectedExeHash = ""

    if (Test-Path $buildValidation) {

        $buildMetadata = Get-Content `
            $buildValidation `
            -Raw

        $buildNumber = Get-MetadataValue `
            $buildMetadata `
            "Build"

        $buildVersion = Get-MetadataValue `
            $buildMetadata `
            "Version"

        $buildCommit = Get-MetadataValue `
            $buildMetadata `
            "Commit"

        $expectedExeHash = Get-MetadataValue `
            $buildMetadata `
            "EXE SHA256"

        Add-Check `
            "Identificacao do Build" `
            (-not [string]::IsNullOrWhiteSpace($buildNumber)) `
            "Build $buildNumber"

        Add-Check `
            "Versao do Agent" `
            ($buildVersion -match '^\d+\.\d+\.\d+$') `
            "versao $buildVersion"

        Add-Check `
            "Commit da Build" `
            ($buildCommit -match '^[0-9a-fA-F]{40}$') `
            $buildCommit
    }

    # ========================================================
    # 3. VERSAO DO INSTALADOR X BUILD
    # ========================================================

    $installerPath = Join-Path `
        $baseDir `
        "Install-PRINTFLOW-Agent.ps1"

    if (
        (Test-Path $installerPath) -and
        -not [string]::IsNullOrWhiteSpace($buildVersion)
    ) {

        $installerText = Get-Content `
            $installerPath `
            -Raw

        # Release Unificada:
        # o instalador pode consumir a versao dinamicamente
        # diretamente do BUILD-VALIDATION.txt.

        $usesDynamicVersion = (
            $installerText -match 'BUILD-VALIDATION\.txt' -and
            $installerText -match '\$agentVersion\s*=\s*\$versionMatch\.Groups\[1\]\.Value' -and
            $installerText -match 'agent_version\s*=\s*\$agentVersion'
        )

        $installerVersionMatch = [regex]::Match(
            $installerText,
            'agent_version\s*=\s*"([^"]+)"'
        )

        $installerVersion = if ($usesDynamicVersion) {
            $buildVersion
        }
        elseif ($installerVersionMatch.Success) {
            $installerVersionMatch.Groups[1].Value
        }
        else {
            ""
        }

        $installerVersionAligned = (
            $installerVersion -eq $buildVersion
        )

        $versionDetail = if ($usesDynamicVersion) {
            "dinamica via BUILD-VALIDATION.txt | build $buildVersion"
        }
        else {
            "instalador $installerVersion | build $buildVersion"
        }

        Add-Check `
            "Versao alinhada no instalador" `
            $installerVersionAligned `
            $versionDetail
    }

    # ========================================================
    # 4. EXECUTAVEL
    # ========================================================

    $exe = Join-Path `
        $baseDir `
        "PRINTFLOW-Agent.exe"

    if (Test-Path $exe) {

        $hash = (
            Get-FileHash `
                $exe `
                -Algorithm SHA256
        ).Hash

        Add-Check `
            "Integridade do executavel" `
            ($hash.Length -eq 64) `
            "SHA256 $hash"

        if (
            -not [string]::IsNullOrWhiteSpace(
                $expectedExeHash
            )
        ) {

            Add-Check `
                "SHA256 confere com a Build" `
                ($hash -eq $expectedExeHash) `
                "hash do executavel confere com BUILD-VALIDATION.txt"
        }

        $help = & $exe --help 2>&1 |
            Out-String

        Add-Check `
            "Inicializacao do executavel" `
            ($LASTEXITCODE -eq 0) `
            "teste --help"

        Add-Check `
            "Modo automatico" `
            ($help -match "--daemon") `
            "opcao disponivel"

        Add-Check `
            "Suporte multi-rede" `
            ($help -match "--network") `
            "opcao --network disponivel"
    }

    # ========================================================
    # 5. INSTALACAO WINDOWS
    #
    # A validacao do PACOTE nao deve falhar por causa de uma
    # instalacao antiga existente em outra pasta.
    # ========================================================

    $task = Get-ScheduledTask -TaskName "PRINTFLOW Agent" -ErrorAction SilentlyContinue

    if ($task) {

        $actionText = (
            $task.Actions |
                ForEach-Object {
                    "$($_.Execute) $($_.Arguments) $($_.WorkingDirectory)"
                }
        ) -join " "

        $currentBase = (
            [System.IO.Path]::GetFullPath($baseDir)
        ).TrimEnd("\")

        $taskBelongsToCurrentPackage = (
            $actionText -like "*$currentBase*"
        )

        if ($taskBelongsToCurrentPackage) {

            Add-Check `
                "Instalacao no Windows" `
                $true `
                "tarefa encontrada para este pacote: $($task.State)"

            Add-Check `
                "Fila do Agent" `
                ($task.State -ne "Queued") `
                "estado $($task.State)"

            $taskInfo = Get-ScheduledTaskInfo `
                -TaskName "PRINTFLOW Agent"

            # Usa Int64 para aceitar todos os codigos retornados
            # pelo Task Scheduler sem overflow de Int32.
            $lastResult = [long]$taskInfo.LastTaskResult

            $taskIsRunning = (
                $task.State -eq "Running" -and
                $lastResult -eq 267009
            )

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

            Add-Check `
                "Ultima execucao" `
                $lastRunHealthy `
                $lastRunDetail
        }
        else {

            Add-Check `
                "Instalacao no Windows" `
                $true `
                "existe uma instalacao anterior em outra pasta; Build atual ainda nao instalado"
        }
    }
    else {

        Add-Check `
            "Instalacao no Windows" `
            $true `
            "Build ainda nao instalado; validacao do pacote concluida"
    }
}
catch {

    Add-Check `
        "Execucao da validacao" `
        $false `
        $_.Exception.Message
}

$overall = if ($failed) {
    "ATENCAO"
}
else {
    "APROVADO"
}

@(
    "PRINTFLOW - RESULTADO DA VALIDACAO"
    "Data: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    "Resultado: $overall"
    ""
    $checks
) |
    Set-Content `
        $resultPath `
        -Encoding UTF8

Get-Content $resultPath

Write-Host ""
Write-Host "Relatorio salvo em: $resultPath"

if ($failed) {
    exit 1
}

exit 0
