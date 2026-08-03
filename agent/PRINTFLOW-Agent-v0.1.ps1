param(
    [string]$PrinterIP = "10.2.0.124",
    [string]$ApiUrl = "https://printflow-api-3uwr.onrender.com"
)

$ErrorActionPreference = "Stop"
Write-Host "PRINTFLOW Agent v0.1" -ForegroundColor Cyan
Write-Host "Testando impressora $PrinterIP..."

$online = Test-Connection -ComputerName $PrinterIP -Count 2 -Quiet
if (-not $online) {
    Write-Host "Impressora offline ou inacessivel." -ForegroundColor Red
    exit 1
}

Write-Host "Ping OK." -ForegroundColor Green

$manufacturer = "HP"
$model = "Laser MFP 432"
$name = "HP Laser MFP 432"
$httpDetected = $false

try {
    $response = Invoke-WebRequest -Uri "http://$PrinterIP" -UseBasicParsing -TimeoutSec 8
    $httpDetected = $true
    $page = $response.Content
    if ($page -match "(?i)HP") { $manufacturer = "HP" }
    if ($page -match "(?i)(LaserJet|Laser MFP|MFP 432|432)") {
        $model = "HP Laser MFP 432"
        $name = $model
    }
    Write-Host "Interface HTTP detectada." -ForegroundColor Green
}
catch {
    Write-Host "Interface HTTP nao respondeu, mas o equipamento esta online." -ForegroundColor Yellow
}

$payload = @{
    ip = $PrinterIP
    name = $name
    manufacturer = $manufacturer
    model = $model
    status = "online"
    source = $(if ($httpDetected) { "agent-http" } else { "agent-ping" })
    page_count = $null
} | ConvertTo-Json

Write-Host "Enviando para a nuvem..."
try {
    $result = Invoke-RestMethod -Uri "$ApiUrl/api/v1/printers/agent" -Method Post -ContentType "application/json" -Body $payload -TimeoutSec 30
    Write-Host "SUCESSO: impressora registrada na nuvem." -ForegroundColor Green
    Write-Host "ID: $($result.id)"
    Write-Host "UUID: $($result.uuid)"
    Write-Host "IP: $($result.ip)"
    Write-Host "Modelo: $($result.model)"
}
catch {
    Write-Host "FALHA ao enviar para a API." -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 2
}

Read-Host "Pressione ENTER para fechar"
