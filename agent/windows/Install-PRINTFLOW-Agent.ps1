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

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$configDirectory = Join-Path $root "config"
$configPath = Join-Path $configDirectory "agent-config.json"
$launcher = Join-Path $root "Start-PRINTFLOW-Agent.ps1"
$diagnosticPath = Join-Path $root "INSTALL-DIAGNOSTICO.txt"

try {

    Write-Host "Configuracao segura do PRINTFLOW Agent"
    Write-Host "Lendo o Token do Agent diretamente da area de transferencia."

    $plainToken = [string](Get-Clipboard -Raw)
    $plainToken = $plainToken.Trim()

    if ($plainToken -notmatch '^[A-Za-z0-9_-]{43}$') {

        throw (
            "Token incorreto ($($plainToken.Length) caracteres). " +
            "Copie o Token do Agent de 43 caracteres; " +
            "nao copie o token de sessao do painel."
        )
    }

    $validationBody = @{
        agent_token = $plainToken
        agent_name = "PRINTFLOW Agent Windows Installer"
        agent_version = "0.3.0"
        status = "starting"
    } | ConvertTo-Json

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
            "Copie o token atual do Dashboard e tente novamente."
        )
    }

    $validationBody = $null

    $token = ConvertTo-SecureString `
        $plainToken `
        -AsPlainText `
        -Force

    $encryptedToken = $token |
        ConvertFrom-SecureString

    $plainToken = $null

    Set-Clipboard -Value "[PRINTFLOW token protegido]"

    $networkInput = Read-Host `
        "Redes adicionais em CIDR separadas por virgula ou ENTER para descoberta automatica"

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

    New-Item `
        -ItemType Directory `
        -Force `
        -Path $configDirectory |
        Out-Null

    @{
        encrypted_token = $encryptedToken

        # Novo formato Multi-Rede V3
        extra_networks = $extraNetworks

        # Compatibilidade com Builds anteriores
        extra_network = ($extraNetworks -join ",")

        configured_at = (
            Get-Date
        ).ToUniversalTime().ToString("o")

    } |
        ConvertTo-Json |
        Set-Content `
            -LiteralPath $configPath `
            -Encoding UTF8

    $taskName = "PRINTFLOW Agent"

    $existingTask = Get-ScheduledTask `
        -TaskName $taskName `
        -ErrorAction SilentlyContinue

    if ($existingTask) {

        Stop-ScheduledTask `
            -TaskName $taskName `
            -ErrorAction SilentlyContinue

        Unregister-ScheduledTask `
            -TaskName $taskName `
            -Confirm:$false
    }

    Get-Process `
        -Name "PRINTFLOW-Agent" `
        -ErrorAction SilentlyContinue |
        Stop-Process `
            -Force `
            -ErrorAction SilentlyContinue

    $powerShell = (
        Get-Command powershell.exe
    ).Source

    $arguments = (
        "-NoLogo -NoProfile -WindowStyle Hidden " +
        "-ExecutionPolicy Bypass -File `"$launcher`""
    )

    $action = New-ScheduledTaskAction `
        -Execute $powerShell `
        -Argument $arguments

    $triggerAtLogon = New-ScheduledTaskTrigger `
        -AtLogOn `
        -User $env:USERNAME

    $triggerRecurring = New-ScheduledTaskTrigger `
        -Once `
        -At (Get-Date).AddMinutes(15) `
        -RepetitionInterval (New-TimeSpan -Minutes 15) `
        -RepetitionDuration (New-TimeSpan -Days 3650)

    $settings = New-ScheduledTaskSettingsSet `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger @(
            $triggerAtLogon,
            $triggerRecurring
        ) `
        -Settings $settings `
        -Description "Monitoramento PRINTFLOW a cada 15 minutos" `
        -Force |
        Out-Null

    Start-ScheduledTask `
        -TaskName $taskName

    Start-Sleep -Seconds 3

    $installedTask = Get-ScheduledTask `
        -TaskName $taskName

    if ($installedTask.State -eq "Queued") {

        throw (
            "A tarefa do Agent permaneceu em espera. " +
            "Consulte INSTALL-DIAGNOSTICO.txt."
        )
    }

    Write-Host `
        "PRINTFLOW Agent instalado e iniciado com sucesso." `
        -ForegroundColor Green

    @(
        "PRINTFLOW Agent - instalacao concluida"
        "Data: $((Get-Date).ToString('o'))"
        "Tarefa: $taskName"
        "Configuracao: $configPath"
        "Redes adicionais: $($extraNetworks -join ', ')"
    ) |
        Set-Content `
            -LiteralPath $diagnosticPath `
            -Encoding UTF8

    Read-Host "Pressione ENTER para fechar"
}
catch {

    $message = $_.Exception.Message

    Write-Host ""
    Write-Host `
        "NAO FOI POSSIVEL INSTALAR O PRINTFLOW AGENT" `
        -ForegroundColor Red

    Write-Host `
        $message `
        -ForegroundColor Red

    @(
        "PRINTFLOW Agent - falha na instalacao"
        "Data: $((Get-Date).ToString('o'))"
        "Erro: $message"
        "Detalhes: $($_ | Out-String)"
    ) |
        Set-Content `
            -LiteralPath $diagnosticPath `
            -Encoding UTF8

    Write-Host `
        "Diagnostico salvo em: $diagnosticPath" `
        -ForegroundColor Yellow

    Read-Host "Pressione ENTER para fechar"

    exit 1
}