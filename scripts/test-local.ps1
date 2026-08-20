$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Ambiente virtual ausente. Execute scripts/setup-local.ps1 primeiro."
}

Set-Location -LiteralPath $ProjectRoot
$env:PYTHONPATH = Join-Path $ProjectRoot "agent\python"

Write-Host "Executando testes do PRINTFLOW Agent..."
& $venvPython -m pytest -q agent\python\tests

if ($LASTEXITCODE -ne 0) {
    throw "Testes do Agent falharam."
}

$npm = Get-Command npm -ErrorAction SilentlyContinue
if ($npm -and (Test-Path -LiteralPath "frontend\node_modules")) {
    Write-Host "Validando frontend..."
    Push-Location frontend
    try {
        & npm run build
        if ($LASTEXITCODE -ne 0) {
            throw "Build do frontend falhou."
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "Validacao local concluida com sucesso."
