$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

function Find-Python312 {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        & py -3.12 --version *> $null
        if ($LASTEXITCODE -eq 0) {
            return @("py", "-3.12")
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($version -eq "3.12") {
            return @("python")
        }
    }

    $codexRuntimeRoot = Join-Path $env:USERPROFILE ".cache\codex-runtimes"
    if (Test-Path -LiteralPath $codexRuntimeRoot) {
        $codexPython = Get-ChildItem `
            -LiteralPath $codexRuntimeRoot `
            -Filter python.exe `
            -Recurse `
            -ErrorAction SilentlyContinue |
            Where-Object {
                $_.FullName -like "*dependencies\python\python.exe"
            } |
            Select-Object -First 1

        if ($codexPython) {
            $version = & $codexPython.FullName -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
            if ($version -eq "3.12") {
                return @($codexPython.FullName)
            }
        }
    }

    throw "Python 3.12 nao encontrado. Instale o Python 3.12 e execute novamente."
}

$pythonCommand = Find-Python312
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Criando ambiente virtual Python 3.12..."
    if ($pythonCommand.Count -eq 2) {
        & $pythonCommand[0] $pythonCommand[1] -m venv .venv
    }
    else {
        & $pythonCommand[0] -m venv .venv
    }
}

Write-Host "Instalando dependencias Python..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements-dev.txt

$node = Get-Command node -ErrorAction SilentlyContinue
$npm = Get-Command npm -ErrorAction SilentlyContinue

if ($node -and $npm) {
    Write-Host "Instalando dependencias do frontend..."
    Push-Location frontend
    try {
        & npm install
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "Node.js nao encontrado; frontend ignorado nesta etapa."
}

Write-Host "Ambiente local preparado com sucesso."
Write-Host "Execute: powershell -ExecutionPolicy Bypass -File scripts/test-local.ps1"
