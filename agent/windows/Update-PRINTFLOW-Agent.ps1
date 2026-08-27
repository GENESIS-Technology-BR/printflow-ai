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
        "-NoLogo -NoProfile -NoExit -ExecutionPolicy Bypass -File `"$scriptPath`""

    exit
}

$ErrorActionPreference = "Stop"

$sourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$installRoot = Join-Path `
    $env:ProgramData `
    "PRINTFLOW\Agent"

$configDirectory = Join-Path `
    $installRoot `
    "config"

$configPath = Join-Path `
    $configDirectory `
    "agent-config.json"

$backupRoot = Join-Path `
    $env:ProgramData `
    "PRINTFLOW\Backups"

$taskName = "PRINTFLOW Agent"

$buildValidationPath = Join-Path `
    $sourceRoot `
    "BUILD-VALIDATION.txt"

$backupPath = $null
$backupReady = $false


function Stop-PrintflowAgent {

    Write-Host ""
    Write-Host "Parando PRINTFLOW Agent..."

    $task = Get-ScheduledTask `
        -TaskName $taskName `
        -ErrorAction SilentlyContinue

    if ($task) {

        Stop-ScheduledTask `
            -TaskName $taskName `
            -ErrorAction SilentlyContinue
    }

    $processes = @(
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
        }
    )

    foreach ($process in $processes) {

        Stop-Process `
            -Id $process.ProcessId `
            -Force `
            -ErrorAction SilentlyContinue
    }

    for ($attempt = 1; $attempt -le 10; $attempt++) {

        Start-Sleep -Seconds 1

        $remaining = @(
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
            }
        )

        if ($remaining.Count -eq 0) {
            break
        }
    }

    Write-Host "[OK] Agent parado." -ForegroundColor Green
}


function Set-PrintflowConfigPermissions {

    & icacls.exe `
        $configDirectory `
        /inheritance:r `
        /grant:r `
        "*S-1-5-18:(OI)(CI)F" `
        "*S-1-5-32-544:(OI)(CI)F" `
        /T `
        /C |
        Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel proteger a pasta config."
    }

    & takeown.exe `
        /F $configPath `
        /A |
        Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel assumir propriedade do agent-config.json."
    }

    & icacls.exe `
        $configPath `
        /inheritance:r `
        /grant:r `
        "*S-1-5-18:F" `
        "*S-1-5-32-544:F" |
        Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel proteger agent-config.json."
    }
}


function Register-PrintflowTask {

    $existingTask = Get-ScheduledTask `
        -TaskName $taskName `
        -ErrorAction SilentlyContinue

    if ($existingTask) {

        Unregister-ScheduledTask `
            -TaskName $taskName `
            -Confirm:$false
    }

    $launcher = Join-Path `
        $installRoot `
        "Start-PRINTFLOW-Agent.ps1"

    $powershell = Join-Path `
        $env:SystemRoot `
        "System32\WindowsPowerShell\v1.0\powershell.exe"

    $arguments = (
        "-NoLogo -NoProfile -WindowStyle Hidden " +
        "-ExecutionPolicy Bypass " +
        "-File `"$launcher`" -Daemon"
    )

    $action = New-ScheduledTaskAction `
        -Execute $powershell `
        -Argument $arguments `
        -WorkingDirectory $installRoot

    $trigger = New-ScheduledTaskTrigger `
        -AtStartup

    $principal = New-ScheduledTaskPrincipal `
        -UserId "SYSTEM" `
        -LogonType ServiceAccount `
        -RunLevel Highest

    $settings = New-ScheduledTaskSettingsSet `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description "PRINTFLOW Agent residente - SYSTEM - inicializacao no boot" `
        -Force |
        Out-Null
}


function Start-AndValidatePrintflowAgent {

    Start-ScheduledTask `
        -TaskName $taskName

    $agentProcess = $null

    for ($attempt = 1; $attempt -le 20; $attempt++) {

        Start-Sleep -Seconds 1

        $agentProcess = (
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
            Select-Object -First 1
        )

        if ($agentProcess) {
            break
        }
    }

    $task = Get-ScheduledTask `
        -TaskName $taskName

    $taskInfo = Get-ScheduledTaskInfo `
        -TaskName $taskName

    if ($task.State -ne "Running") {

        throw (
            "Tarefa PRINTFLOW nao permaneceu Running. " +
            "Estado=$($task.State) " +
            "Resultado=$($taskInfo.LastTaskResult)"
        )
    }

    if (-not $agentProcess) {

        throw (
            "PRINTFLOW-Agent.exe nao foi localizado " +
            "apos a atualizacao."
        )
    }

    return $agentProcess
}


function Restore-PrintflowBackup {

    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " ROLLBACK PRINTFLOW"
    Write-Host "============================================================" `
        -ForegroundColor Yellow

    Stop-PrintflowAgent

    $runtimeBackup = Join-Path `
        $Path `
        "runtime"

    $configBackup = Join-Path `
        $Path `
        "config"

    if (-not (Test-Path $runtimeBackup)) {
        throw "Backup de runtime nao encontrado."
    }

    if (-not (Test-Path $configBackup)) {
        throw "Backup de configuracao nao encontrado."
    }

    Get-ChildItem `
        $runtimeBackup `
        -File |
    ForEach-Object {

        Copy-Item `
            -LiteralPath $_.FullName `
            -Destination $installRoot `
            -Force
    }

    if (Test-Path $configDirectory) {

        Remove-Item `
            $configDirectory `
            -Recurse `
            -Force
    }

    Copy-Item `
        -LiteralPath $configBackup `
        -Destination $configDirectory `
        -Recurse `
        -Force

    Set-PrintflowConfigPermissions

    Register-PrintflowTask

    $process = Start-AndValidatePrintflowAgent

    Write-Host ""
    Write-Host "[OK] ROLLBACK CONCLUIDO." `
        -ForegroundColor Green

    Write-Host "PID restaurado:" $process.ProcessId
}


try {

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " PRINTFLOW - ATUALIZACAO SEGURA"
    Write-Host "============================================================"

    if (-not (Test-Path $installRoot)) {

        throw (
            "PRINTFLOW ainda nao esta instalado. " +
            "Use INSTALAR-PRINTFLOW-Agent.bat."
        )
    }

    if (-not (Test-Path $configPath)) {

        throw (
            "Configuracao existente nao encontrada. " +
            "Use INSTALAR-PRINTFLOW-Agent.bat."
        )
    }

    if (-not (Test-Path $buildValidationPath)) {

        throw "BUILD-VALIDATION.txt nao encontrado."
    }

    $metadata = Get-Content `
        $buildValidationPath `
        -Raw `
        -ErrorAction Stop

    $versionMatch = [regex]::Match(
        $metadata,
        '(?m)^Version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$'
    )

    if (-not $versionMatch.Success) {
        throw "Versao da nova Build nao encontrada."
    }

    $newVersion = $versionMatch.Groups[1].Value

    Write-Host "Nova versao:" $newVersion

    Write-Host ""
    Write-Host "===== LENDO CONFIGURACAO EXISTENTE ====="

    $savedConfig = (
        Get-Content `
            -LiteralPath $configPath `
            -Raw `
            -ErrorAction Stop |
        ConvertFrom-Json `
            -ErrorAction Stop
    )

    if (
        -not (
            $savedConfig.PSObject.Properties.Name -contains
            "encrypted_token_machine"
        ) -or
        [string]::IsNullOrWhiteSpace(
            [string]$savedConfig.encrypted_token_machine
        )
    ) {

        throw (
            "Token protegido por maquina nao encontrado. " +
            "Atualizacao automatica cancelada."
        )
    }

    $oldVersion = [string]$savedConfig.agent_version

    if ([string]::IsNullOrWhiteSpace($oldVersion)) {
        $oldVersion = "desconhecida"
    }

    $tokenBefore = [string]$savedConfig.encrypted_token_machine

    $networksBefore = @(
        $savedConfig.extra_networks
    ) -join "|"

    $legacyNetworksBefore = [string]$savedConfig.extra_network

    Write-Host "Versao instalada:" $oldVersion
    Write-Host "Token            : PRESERVADO - NAO EXIBIDO"

    Write-Host "Redes existentes :"

    @($savedConfig.extra_networks) |
    ForEach-Object {
        Write-Host " -" $_
    }

    Write-Host ""
    Write-Host "===== CRIANDO BACKUP ====="

    New-Item `
        -ItemType Directory `
        -Force `
        -Path $backupRoot |
        Out-Null

    $backupPath = Join-Path `
        $backupRoot `
        (
            "Agent-" +
            (Get-Date -Format "yyyyMMdd-HHmmss")
        )

    $runtimeBackup = Join-Path `
        $backupPath `
        "runtime"

    $configBackup = Join-Path `
        $backupPath `
        "config"

    New-Item `
        -ItemType Directory `
        -Force `
        -Path $runtimeBackup |
        Out-Null

    foreach ($runtimeFile in @(
        "PRINTFLOW-Agent.exe",
        "Start-PRINTFLOW-Agent.ps1",
        "Uninstall-PRINTFLOW-Agent.ps1",
        "BUILD-VALIDATION.txt",
        "README-TESTE.txt"
    )) {

        $installedFile = Join-Path `
            $installRoot `
            $runtimeFile

        if (Test-Path $installedFile) {

            Copy-Item `
                -LiteralPath $installedFile `
                -Destination $runtimeBackup `
                -Force
        }
    }

    Copy-Item `
        -LiteralPath $configDirectory `
        -Destination $configBackup `
        -Recurse `
        -Force

    $backupReady = $true

    Write-Host "[OK] Backup criado:"
    Write-Host $backupPath

    Write-Host ""
    Write-Host "===== PARANDO VERSAO ANTERIOR ====="

    Stop-PrintflowAgent

    Write-Host ""
    Write-Host "===== ATUALIZANDO RUNTIME ====="

    foreach ($runtimeFile in @(
        "PRINTFLOW-Agent.exe",
        "Start-PRINTFLOW-Agent.ps1",
        "Uninstall-PRINTFLOW-Agent.ps1",
        "BUILD-VALIDATION.txt",
        "README-TESTE.txt"
    )) {

        $sourceFile = Join-Path `
            $sourceRoot `
            $runtimeFile

        if (-not (Test-Path $sourceFile)) {
            throw "Arquivo ausente na Build: $runtimeFile"
        }

        Copy-Item `
            -LiteralPath $sourceFile `
            -Destination $installRoot `
            -Force
    }

    Write-Host "[OK] Runtime atualizado."

    Write-Host ""
    Write-Host "===== PRESERVANDO CONFIGURACAO ====="

    $savedConfig.agent_version = $newVersion

    if (
        $savedConfig.PSObject.Properties.Name -contains
        "updated_at"
    ) {

        $savedConfig.updated_at = (
            Get-Date
        ).ToUniversalTime().ToString("o")
    }
    else {

        $savedConfig |
        Add-Member `
            -NotePropertyName "updated_at" `
            -NotePropertyValue (
                (Get-Date).ToUniversalTime().ToString("o")
            )
    }

    $savedConfig |
        ConvertTo-Json -Depth 10 |
        Set-Content `
            -LiteralPath $configPath `
            -Encoding UTF8

    Set-PrintflowConfigPermissions

    $configCheck = (
        Get-Content `
            -LiteralPath $configPath `
            -Raw `
            -ErrorAction Stop |
        ConvertFrom-Json `
            -ErrorAction Stop
    )

    $tokenAfter = [string]$configCheck.encrypted_token_machine

    $networksAfter = @(
        $configCheck.extra_networks
    ) -join "|"

    $legacyNetworksAfter = [string]$configCheck.extra_network

    if ($tokenAfter -ne $tokenBefore) {
        throw "Token foi alterado durante a atualizacao."
    }

    if ($networksAfter -ne $networksBefore) {
        throw "Lista de redes foi alterada durante a atualizacao."
    }

    if ($legacyNetworksAfter -ne $legacyNetworksBefore) {
        throw "Rede legada foi alterada durante a atualizacao."
    }

    Write-Host "[OK] Token preservado."
    Write-Host "[OK] Redes preservadas."
    Write-Host "[OK] ACL validada."

    Write-Host ""
    Write-Host "===== RECRIANDO TAREFA SYSTEM ====="

    Register-PrintflowTask

    Write-Host "[OK] Tarefa SYSTEM criada."

    Write-Host ""
    Write-Host "===== INICIANDO NOVA VERSAO ====="

    $agentProcess = Start-AndValidatePrintflowAgent

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " PRINTFLOW ATUALIZADO COM SUCESSO" `
        -ForegroundColor Green
    Write-Host "============================================================"
    Write-Host "Versao anterior :" $oldVersion
    Write-Host "Nova versao     :" $newVersion
    Write-Host "Token           : PRESERVADO"
    Write-Host "Redes           : PRESERVADAS"
    Write-Host "Usuario         : SYSTEM"
    Write-Host "Estado          : Running"
    Write-Host "PID             :" $agentProcess.ProcessId
    Write-Host "Backup          :" $backupPath
    Write-Host "============================================================"

    Read-Host "Pressione ENTER para fechar"
}
catch {

    $updateError = $_.Exception.Message

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " FALHA NA ATUALIZACAO PRINTFLOW" `
        -ForegroundColor Red
    Write-Host "============================================================"

    Write-Host $updateError `
        -ForegroundColor Red

    if (
        $backupReady -and
        $backupPath -and
        (Test-Path $backupPath)
    ) {

        try {

            Restore-PrintflowBackup `
                -Path $backupPath

            Write-Host ""
            Write-Host (
                "[SEGURANCA] A versao anterior foi restaurada."
            ) -ForegroundColor Green
        }
        catch {

            Write-Host ""
            Write-Host (
                "[CRITICO] O rollback automatico tambem falhou: " +
                $_.Exception.Message
            ) -ForegroundColor Red
        }
    }

    Read-Host "Pressione ENTER para fechar"

    exit 1
}