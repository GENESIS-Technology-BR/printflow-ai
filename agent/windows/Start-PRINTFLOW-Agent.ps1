param(
    [switch]$Daemon
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Security

$agentDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path

$executable = Join-Path `
    $agentDirectory `
    "PRINTFLOW-Agent.exe"

if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {

    Write-Host `
        "ERRO: PRINTFLOW-Agent.exe nao foi encontrado." `
        -ForegroundColor Red

    if (-not $Daemon) {
        Read-Host "Pressione ENTER para sair"
    }

    exit 1
}

$configPath = Join-Path `
    $agentDirectory `
    "config\agent-config.json"

$savedConfig = $null

if (Test-Path -LiteralPath $configPath) {

    $savedConfig = (
        Get-Content `
            -LiteralPath $configPath `
            -Raw |
        ConvertFrom-Json
    )
}


function Unprotect-PrintflowToken {
    param(
        [Parameter(Mandatory)]
        [string]$EncryptedToken
    )

    $protectedBytes = [Convert]::FromBase64String(
        $EncryptedToken
    )

    try {

        $plainBytes = (
            [Security.Cryptography.ProtectedData]::Unprotect(
                $protectedBytes,
                $null,
                [Security.Cryptography.DataProtectionScope]::LocalMachine
            )
        )

        try {

            return [Text.Encoding]::UTF8.GetString(
                $plainBytes
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
    finally {

        if ($protectedBytes) {

            [Array]::Clear(
                $protectedBytes,
                0,
                $protectedBytes.Length
            )
        }
    }
}


$plainToken = $null
$tokenPointer = [IntPtr]::Zero

try {

    # ============================================================
    # TOKEN LOCAL MACHINE
    # ============================================================

    if (
        $savedConfig -and
        $savedConfig.PSObject.Properties.Name -contains
            "encrypted_token_machine" -and
        -not [string]::IsNullOrWhiteSpace(
            [string]$savedConfig.encrypted_token_machine
        )
    ) {

        $plainToken = Unprotect-PrintflowToken `
            -EncryptedToken (
                [string]$savedConfig.encrypted_token_machine
            )
    }
    elseif (
        $savedConfig -and
        $savedConfig.PSObject.Properties.Name -contains
            "encrypted_token" -and
        $savedConfig.encrypted_token
    ) {

        # Compatibilidade somente para instalacoes antigas.
        # Pode falhar se outro usuario criou o token.
        $secureToken = (
            $savedConfig.encrypted_token |
            ConvertTo-SecureString
        )

        $tokenPointer = (
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR(
                $secureToken
            )
        )

        $plainToken = (
            [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
                $tokenPointer
            )
        )
    }
    elseif ($Daemon) {

        throw (
            "Agent nao configurado para execucao automatica. " +
            "Execute Install-PRINTFLOW-Agent.ps1."
        )
    }
    else {

        $secureToken = Read-Host `
            "Digite ou cole o Token do Agent" `
            -AsSecureString

        $tokenPointer = (
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR(
                $secureToken
            )
        )

        $plainToken = (
            [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
                $tokenPointer
            )
        )
    }

    if (
        [string]::IsNullOrWhiteSpace($plainToken) -or
        $plainToken -notmatch '^[A-Za-z0-9_-]{43}$'
    ) {

        throw (
            "Token local invalido. " +
            "Execute Install-PRINTFLOW-Agent.ps1 novamente."
        )
    }

    # ============================================================
    # MULTI-REDE
    # ============================================================

    $extraNetworks = @()

    if ($savedConfig) {

        if (
            $savedConfig.PSObject.Properties.Name -contains
                "extra_networks" -and
            $savedConfig.extra_networks
        ) {

            $extraNetworks = @(
                $savedConfig.extra_networks
            )
        }
        elseif (
            $savedConfig.PSObject.Properties.Name -contains
                "extra_network" -and
            -not [string]::IsNullOrWhiteSpace(
                [string]$savedConfig.extra_network
            )
        ) {

            $extraNetworks = @(
                [regex]::Split(
                    [string]$savedConfig.extra_network,
                    '[,;]+'
                )
            )
        }
    }
    elseif (-not $Daemon) {

        $manualNetworks = Read-Host `
            "Informe redes adicionais em CIDR separadas por virgula ou pressione ENTER"

        if (
            -not [string]::IsNullOrWhiteSpace(
                $manualNetworks
            )
        ) {

            $extraNetworks = @(
                [regex]::Split(
                    $manualNetworks,
                    '[,;]+'
                )
            )
        }
    }

    $extraNetworks = @(
        $extraNetworks |
            ForEach-Object {
                [string]$_
            } |
            ForEach-Object {
                $_.Trim()
            } |
            Where-Object {
                -not [string]::IsNullOrWhiteSpace($_)
            } |
            Select-Object -Unique
    )

    # ============================================================
    # ARGUMENTOS DO EXE
    # ============================================================

    $arguments = @()

    foreach ($extraNetwork in $extraNetworks) {

        $arguments += "--network"
        $arguments += $extraNetwork
    }

    if ($Daemon) {
        $arguments += "--daemon"
    }

    # ============================================================
    # PROCESSO FILHO COM AMBIENTE ISOLADO
    # ============================================================

    $processInfo = New-Object `
        System.Diagnostics.ProcessStartInfo

    $processInfo.FileName = $executable
    $processInfo.WorkingDirectory = $agentDirectory
    $processInfo.UseShellExecute = $false
    $processInfo.CreateNoWindow = $Daemon.IsPresent

    $escapedArguments = @(
        $arguments |
            ForEach-Object {

                if ($_ -match '\s') {

                    '"' +
                    $_.Replace('"', '\"') +
                    '"'
                }
                else {
                    $_
                }
            }
    )

    $processInfo.Arguments = (
        $escapedArguments -join " "
    )

    $processInfo.EnvironmentVariables[
        "PRINTFLOW_AGENT_TOKEN"
    ] = $plainToken

    $processInfo.EnvironmentVariables[
        "PRINTFLOW_API_URL"
    ] = "https://printflow-api-genesis.onrender.com"

    $processInfo.EnvironmentVariables[
        "PRINTFLOW_AGENT_NAME"
    ] = "PRINTFLOW Agent Windows"

    $processInfo.EnvironmentVariables[
        "PRINTFLOW_SCAN_INTERVAL"
    ] = "900"

    $processInfo.EnvironmentVariables[
        "PRINTFLOW_MAXIMUM_HOSTS"
    ] = "1024"

    $processInfo.EnvironmentVariables[
        "PRINTFLOW_SNMP_COMMUNITY"
    ] = "public"

    $processInfo.EnvironmentVariables[
        "PRINTFLOW_NETWORK_TIMEOUT"
    ] = "0.40"

    $processInfo.EnvironmentVariables[
        "PRINTFLOW_SNMP_TIMEOUT"
    ] = "1.50"

    $processInfo.EnvironmentVariables[
        "PRINTFLOW_SNMP_RETRIES"
    ] = "1"

    $process = (
        [Diagnostics.Process]::Start(
            $processInfo
        )
    )

    # Remove copias em memoria do launcher apos o filho iniciar.
    $processInfo.EnvironmentVariables[
        "PRINTFLOW_AGENT_TOKEN"
    ] = ""

    $plainToken = $null

    if (-not $process) {
        throw "Nao foi possivel iniciar PRINTFLOW-Agent.exe."
    }

    $process.WaitForExit()

    $agentExitCode = $process.ExitCode
}
catch {

    Write-Host `
        "ERRO: $($_.Exception.Message)" `
        -ForegroundColor Red

    $agentExitCode = 1
}
finally {

    $plainToken = $null

    if ($tokenPointer -ne [IntPtr]::Zero) {

        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR(
            $tokenPointer
        )
    }
}

if (-not $Daemon) {

    Write-Host ""
    Write-Host "PRINTFLOW AGENT FINALIZADO"
    Write-Host "Codigo de saida: $agentExitCode"
    Write-Host "Verifique output, logs e o Dashboard."

    Read-Host "Pressione ENTER para continuar"
}

exit $agentExitCode