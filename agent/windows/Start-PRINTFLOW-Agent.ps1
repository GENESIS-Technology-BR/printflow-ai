param([switch]$Daemon)
$ErrorActionPreference = "Stop"

$agentDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$executable = Join-Path $agentDirectory "PRINTFLOW-Agent.exe"

if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    Write-Host "ERRO: PRINTFLOW-Agent.exe nao foi encontrado." -ForegroundColor Red
    Read-Host "Pressione ENTER para sair"
    exit 1
}

Write-Host "============================================================"
Write-Host "PRINTFLOW AGENT - TESTE NA REDE DO CLIENTE"
Write-Host "============================================================"
Write-Host "Pasta do Agent: $agentDirectory"
Write-Host ""

$configPath = Join-Path $agentDirectory "config\agent-config.json"
$savedConfig = $null
if (Test-Path -LiteralPath $configPath) {
    $savedConfig = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
}
$secureToken = if ($savedConfig -and $savedConfig.encrypted_token) {
    $savedConfig.encrypted_token | ConvertTo-SecureString
} elseif ($Daemon) {
    throw "Agent nao configurado. Execute Install-PRINTFLOW-Agent.ps1."
} else {
    Read-Host "Digite ou cole o Token do Agent" -AsSecureString
}
$tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)

try {
    $plainToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
    if (
        [string]::IsNullOrWhiteSpace($plainToken) -or
        $plainToken -notmatch '^[A-Za-z0-9_-]{43}$'
    ) {
        throw "Token local invalido. Execute Install-PRINTFLOW-Agent.ps1 novamente."
    }

    $env:PRINTFLOW_AGENT_TOKEN = $plainToken
    $env:PRINTFLOW_API_URL = "https://printflow-api-genesis.onrender.com"
    $env:PRINTFLOW_AGENT_NAME = "PRINTFLOW Agent Windows"
    $env:PRINTFLOW_SCAN_INTERVAL = "900"
    $env:PRINTFLOW_MAXIMUM_HOSTS = "1024"
    $env:PRINTFLOW_SNMP_COMMUNITY = "public"
    $env:PRINTFLOW_NETWORK_TIMEOUT = "0.40"
    $env:PRINTFLOW_SNMP_TIMEOUT = "1.50"
    $env:PRINTFLOW_SNMP_RETRIES = "1"

    $extraNetwork = if ($savedConfig) {
        [string]$savedConfig.extra_network
    } elseif ($Daemon) {
        ""
    } else {
        Read-Host "Informe uma rede adicional em CIDR ou pressione ENTER"
    }
    $arguments = @()
    if (-not [string]::IsNullOrWhiteSpace($extraNetwork)) {
        $arguments = @("--network", $extraNetwork.Trim())
    }

    if ($Daemon) { $arguments += "--daemon" }
    & $executable @arguments
    $agentExitCode = $LASTEXITCODE
}
catch {
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    $agentExitCode = 1
}
finally {
    $env:PRINTFLOW_AGENT_TOKEN = $null
    $plainToken = $null
    if ($tokenPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer)
    }
}

Write-Host ""
Write-Host "PRINTFLOW AGENT FINALIZADO"
Write-Host "Codigo de saida: $agentExitCode"
Write-Host "Verifique as pastas output e logs e o Dashboard do PRINTFLOW."
if (-not $Daemon) { Read-Host "Pressione ENTER para continuar" }
exit $agentExitCode
