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

Add-Type -AssemblyName System.Security

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

$logsDirectory = Join-Path `
    $installRoot `
    "logs"

$outputDirectory = Join-Path `
    $installRoot `
    "output"

$taskName = "PRINTFLOW Agent"

$sourceDiagnosticPath = Join-Path `
    $sourceRoot `
    "INSTALL-DIAGNOSTICO.txt"

$installedDiagnosticPath = Join-Path `
    $installRoot `
    "INSTALL-DIAGNOSTICO.txt"

$buildValidationPath = Join-Path `
    $sourceRoot `
    "BUILD-VALIDATION.txt"

if (-not (Test-Path $buildValidationPath)) {
    throw "BUILD-VALIDATION.txt nao encontrado no pacote."
}

$buildValidationText = Get-Content `
    $buildValidationPath `
    -Raw

$versionMatch = [regex]::Match(
    $buildValidationText,
    '(?m)^Version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$'
)

if (-not $versionMatch.Success) {
    throw "Nao foi possivel identificar a versao do Agent."
}

$agentVersion = $versionMatch.Groups[1].Value


function Protect-PrintflowToken {
    param(
        [Parameter(Mandatory)]
        [string]$PlainToken
    )

    $plainBytes = [Text.Encoding]::UTF8.GetBytes(
        $PlainToken
    )

    try {

        $protectedBytes = (
            [Security.Cryptography.ProtectedData]::Protect(
                $plainBytes,
                $null,
                [Security.Cryptography.DataProtectionScope]::LocalMachine
            )
        )

        return [Convert]::ToBase64String(
            $protectedBytes
        )
    }
    finally {

        if ($plainBytes) {

            [Array]::Clear(
                $plainBytes,
                0,
                $plainBytes.Length
            )
        }
    }
}


function Set-PrintflowConfigPermissions {

    if (-not (Test-Path $configDirectory)) {
        return
    }

    # ============================================================
    # PASTA CONFIG
    # SYSTEM + ADMINISTRADORES
    # ============================================================

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
        throw "Nao foi possivel proteger a pasta de configuracao."
    }

    if (-not (Test-Path -LiteralPath $configPath)) {
        throw "agent-config.json nao foi criado."
    }

    # ============================================================
    # ARQUIVO CONFIG
    # ACL EXPLICITA PARA EVITAR ACL VAZIA/INVALIDA
    # ============================================================

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

    # ============================================================
    # TESTE REAL DE LEITURA
    # NAO ACEITAMOS FALSO POSITIVO
    # ============================================================

    try {

        $configValidation = (
            Get-Content `
                -LiteralPath $configPath `
                -Raw `
                -ErrorAction Stop |
            ConvertFrom-Json `
                -ErrorAction Stop
        )

        if (-not $configValidation.agent_version) {
            throw "agent_version ausente na configuracao."
        }

        if (
            -not $configValidation.encrypted_token_machine
        ) {
            throw "Token protegido por maquina ausente."
        }
    }
    catch {

        throw (
            "Falha ao validar leitura segura de agent-config.json: " +
            $_.Exception.Message
        )
    }

    $configValidation = $null
}


function Write-InstallDiagnostic {
    param(
        [string[]]$Lines
    )

    foreach ($path in @(
        $sourceDiagnosticPath,
        $installedDiagnosticPath
    )) {

        try {

            $directory = Split-Path -Parent $path

            if (-not (Test-Path $directory)) {

                New-Item `
                    -ItemType Directory `
                    -Force `
                    -Path $directory |
                    Out-Null
            }

            $Lines |
                Set-Content `
                    -LiteralPath $path `
                    -Encoding UTF8
        }
        catch {
            # Diagnostico auxiliar nao deve quebrar a instalacao.
        }
    }
}


try {

    Write-Host ""
    Write-Host "PRINTFLOW Agent Windows v$agentVersion"
    Write-Host "Instalacao residente em:"
    Write-Host $installRoot
    Write-Host ""

    # ============================================================
    # TOKEN
    # ============================================================

    Write-Host "Lendo Token do Agent da area de transferencia."

    $plainToken = [string](
        Get-Clipboard -Raw
    )

    $plainToken = $plainToken.Trim()

    if ($plainToken -notmatch '^[A-Za-z0-9_-]{43}$') {

        throw (
            "Token incorreto ($($plainToken.Length) caracteres). " +
            "No Dashboard > Agents clique em Copiar token e tente novamente."
        )
    }

    $validationBody = @{
        agent_token = $plainToken
        agent_name = "PRINTFLOW Agent Windows Installer"
        agent_version = $agentVersion
        status = "starting"
    } |
        ConvertTo-Json

    try {

        Invoke-RestMethod `
            -Uri "https://printflow-api-genesis.onrender.com/api/v1/printers/agent/heartbeat" `
            -Method Post `
            -ContentType "application/json" `
            -Body $validationBody |
            Out-Null
    }
    catch {

        throw (
            "Token recusado pela API. " +
            "Copie novamente o Token do Agent no Dashboard."
        )
    }

    $validationBody = $null

    Write-Host "[OK] Token validado pela API." -ForegroundColor Green

    # ============================================================
    # MULTI-REDE
    # ============================================================

    Write-Host ""

    $networkInput = Read-Host `
        "Redes adicionais em CIDR separadas por virgula ou ENTER para somente descoberta automatica"

    $extraNetworks = @()

    if (
        -not [string]::IsNullOrWhiteSpace(
            $networkInput
        )
    ) {

        $extraNetworks = @(
            [regex]::Split(
                $networkInput,
                '[,;]+'
            ) |
                ForEach-Object {
                    $_.Trim()
                } |
                Where-Object {
                    -not [string]::IsNullOrWhiteSpace($_)
                } |
                Select-Object -Unique
        )
    }

    foreach ($network in $extraNetworks) {

        try {

            [void][System.Net.IPNetwork]$null
        }
        catch {
            # Tipo nao existe em Windows PowerShell 5.1.
        }

        if (
            $network -notmatch
            '^(\d{1,3}\.){3}\d{1,3}/([0-9]|[12][0-9]|3[0-2])$'
        ) {

            throw "Rede CIDR invalida: $network"
        }
    }

    # ============================================================
    # PARAR INSTALACAO ANTERIOR
    # ============================================================

    Write-Host ""
    Write-Host "Preparando atualizacao..."

    $existingTask = Get-ScheduledTask `
        -TaskName $taskName `
        -ErrorAction SilentlyContinue

    if ($existingTask) {

        Stop-ScheduledTask `
            -TaskName $taskName `
            -ErrorAction SilentlyContinue

        Start-Sleep -Seconds 1

        Unregister-ScheduledTask `
            -TaskName $taskName `
            -Confirm:$false
    }

    Get-CimInstance `
        Win32_Process `
        -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq "PRINTFLOW-Agent.exe"
        } |
        ForEach-Object {

            Stop-Process `
                -Id $_.ProcessId `
                -Force `
                -ErrorAction SilentlyContinue
        }

    # ============================================================
    # CRIAR PROGRAMDATA
    # ============================================================

    foreach ($directory in @(
        $installRoot,
        $configDirectory,
        $logsDirectory,
        $outputDirectory
    )) {

        New-Item `
            -ItemType Directory `
            -Force `
            -Path $directory |
            Out-Null
    }

    # ============================================================
    # COPIAR RUNTIME
    # ============================================================

    $runtimeFiles = @(
        "PRINTFLOW-Agent.exe",
        "Start-PRINTFLOW-Agent.ps1",
        "Uninstall-PRINTFLOW-Agent.ps1",
        "BUILD-VALIDATION.txt",
        "README-TESTE.txt"
    )

    foreach ($runtimeFile in $runtimeFiles) {

        $sourceFile = Join-Path `
            $sourceRoot `
            $runtimeFile

        if (-not (Test-Path $sourceFile)) {
            throw "Arquivo obrigatorio ausente: $runtimeFile"
        }

        Copy-Item `
            -LiteralPath $sourceFile `
            -Destination $installRoot `
            -Force
    }

    # ============================================================
    # DPAPI LOCAL MACHINE
    # ============================================================

    $encryptedTokenMachine = Protect-PrintflowToken `
        -PlainToken $plainToken

    $plainToken = $null

    Set-Clipboard `
        -Value "[PRINTFLOW token protegido]"

    @{
        schema_version = 2

        token_protection = "dpapi-localmachine-v1"

        encrypted_token_machine = $encryptedTokenMachine

        extra_networks = $extraNetworks

        extra_network = (
            $extraNetworks -join ","
        )

        agent_version = $agentVersion

        installed_path = $installRoot

        configured_at = (
            Get-Date
        ).ToUniversalTime().ToString("o")
    } |
        ConvertTo-Json -Depth 5 |
        Set-Content `
            -LiteralPath $configPath `
            -Encoding UTF8

    $encryptedTokenMachine = $null

    Set-PrintflowConfigPermissions

    Write-Host "[OK] Token protegido por MAQUINA." -ForegroundColor Green
    Write-Host "[OK] Config restrita a SYSTEM e Administradores." -ForegroundColor Green

    # ============================================================
    # TAREFA SYSTEM / STARTUP / DAEMON
    # ============================================================

    $installedLauncher = Join-Path `
        $installRoot `
        "Start-PRINTFLOW-Agent.ps1"

    $powerShell = Join-Path `
        $env:SystemRoot `
        "System32\WindowsPowerShell\v1.0\powershell.exe"

    $arguments = (
        "-NoLogo -NoProfile -WindowStyle Hidden " +
        "-ExecutionPolicy Bypass " +
        "-File `"$installedLauncher`" -Daemon"
    )

    $action = New-ScheduledTaskAction `
        -Execute $powerShell `
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

    Start-ScheduledTask `
        -TaskName $taskName

    # ============================================================
    # AGUARDAR INICIALIZACAO
    # ============================================================

    $agentProcess = $null

    for ($attempt = 1; $attempt -le 15; $attempt++) {

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

    $installedTask = Get-ScheduledTask `
        -TaskName $taskName

    $taskInfo = Get-ScheduledTaskInfo `
        -TaskName $taskName

    if ($installedTask.State -ne "Running") {

        throw (
            "A tarefa foi criada, mas nao permaneceu Running. " +
            "Estado=$($installedTask.State) " +
            "Resultado=$($taskInfo.LastTaskResult)"
        )
    }

    if (-not $agentProcess) {

        throw (
            "A tarefa esta Running, mas o processo " +
            "PRINTFLOW-Agent.exe nao foi localizado em ProgramData."
        )
    }

    # ============================================================
    # SUCESSO
    # ============================================================

    $successLines = @(
        "PRINTFLOW Agent - instalacao concluida"
        "Data: $((Get-Date).ToString('o'))"
        "Versao: $agentVersion"
        "Pasta: $installRoot"
        "Tarefa: $taskName"
        "Usuario da tarefa: SYSTEM"
        "Estado: $($installedTask.State)"
        "PID: $($agentProcess.ProcessId)"
        "Token: DPAPI LocalMachine"
        "Redes adicionais: $($extraNetworks -join ', ')"
    )

    Write-InstallDiagnostic `
        -Lines $successLines

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " PRINTFLOW AGENT INSTALADO COM SUCESSO" -ForegroundColor Green
    Write-Host "============================================================"
    Write-Host "Versao :" $agentVersion
    Write-Host "Pasta  :" $installRoot
    Write-Host "Usuario : SYSTEM"
    Write-Host "Estado  :" $installedTask.State
    Write-Host "PID     :" $agentProcess.ProcessId
    Write-Host "Modo    : DAEMON"
    Write-Host ""
    Write-Host "O Agent continuara funcionando mesmo sem usuario logado."
    Write-Host ""

    Read-Host "Pressione ENTER para fechar"
}
catch {

    $message = $_.Exception.Message

    Write-Host ""
    Write-Host "NAO FOI POSSIVEL INSTALAR O PRINTFLOW AGENT" `
        -ForegroundColor Red

    Write-Host $message `
        -ForegroundColor Red

    $failureLines = @(
        "PRINTFLOW Agent - falha na instalacao"
        "Data: $((Get-Date).ToString('o'))"
        "Versao: $agentVersion"
        "Erro: $message"
        "Detalhes: $($_ | Out-String)"
    )

    Write-InstallDiagnostic `
        -Lines $failureLines

    Write-Host ""
    Write-Host "Diagnostico:"
    Write-Host $sourceDiagnosticPath

    Read-Host "Pressione ENTER para fechar"

    exit 1
}
finally {

    $plainToken = $null
    $validationBody = $null
}