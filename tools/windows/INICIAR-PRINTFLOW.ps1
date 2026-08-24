# ============================================================
# PRINTFLOW - INICIALIZADOR OFICIAL DO AMBIENTE LOCAL
# Genesis Technology
# ============================================================

$ErrorActionPreference = "Continue"

$Root = "C:\PRINTFLOW"
$Projeto = "C:\PRINTFLOW\printflow-ai"
$Repo = "https://github.com/GENESIS-Technology-BR/printflow-ai.git"

Clear-Host

Write-Host ""
Write-Host "============================================================"
Write-Host " PRINTFLOW - INICIALIZADOR DO AMBIENTE"
Write-Host "============================================================"
Write-Host ""

# ------------------------------------------------------------
# FUNCOES
# ------------------------------------------------------------

function Atualizar-Path {

    $machine = [Environment]::GetEnvironmentVariable(
        "Path",
        "Machine"
    )

    $user = [Environment]::GetEnvironmentVariable(
        "Path",
        "User"
    )

    $env:Path = "$machine;$user"
}

function Parar-PrintFlow {

    param(
        [string]$Mensagem
    )

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "[ATENCAO] $Mensagem"
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "NAO FOI FEITO COMMIT."
    Write-Host "NAO FOI FEITO PUSH."
    Write-Host ""

    Read-Host "Pressione ENTER para fechar"
    exit 1
}

# ------------------------------------------------------------
# 1. WINGET
# ------------------------------------------------------------

Write-Host "===== 1. WINGET ====="

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {

    Parar-PrintFlow `
        "Winget nao encontrado. Instale/atualize o App Installer."

}

Write-Host "[OK] Winget"

# ------------------------------------------------------------
# 2. GIT
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 2. GIT ====="

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {

    Write-Host "Git nao encontrado. Instalando..."

    winget install `
        --id Git.Git `
        --exact `
        --silent `
        --accept-package-agreements `
        --accept-source-agreements

    Atualizar-Path
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {

    Parar-PrintFlow `
        "Git foi instalado, mas ainda nao ficou disponivel. Reinicie o PowerShell."

}

git --version

# ------------------------------------------------------------
# 3. VS CODE
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 3. VS CODE ====="

if (-not (Get-Command code -ErrorAction SilentlyContinue)) {

    Write-Host "VS Code nao encontrado. Instalando..."

    winget install `
        --id Microsoft.VisualStudioCode `
        --exact `
        --silent `
        --accept-package-agreements `
        --accept-source-agreements

    Atualizar-Path
}

if (Get-Command code -ErrorAction SilentlyContinue) {

    Write-Host "[OK] VS Code encontrado"

}
else {

    Write-Host "[AVISO] VS Code instalado."
    Write-Host "Pode ser necessario reiniciar o PowerShell."

}

# ------------------------------------------------------------
# 4. PYTHON
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 4. PYTHON ====="

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {

    Write-Host "Python nao encontrado. Instalando..."

    winget install `
        --id Python.Python.3.14 `
        --exact `
        --silent `
        --accept-package-agreements `
        --accept-source-agreements

    Atualizar-Path
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {

    Parar-PrintFlow `
        "Python ainda nao esta disponivel. Reinicie o PowerShell."

}

py --version

# ------------------------------------------------------------
# 5. PASTA PRINCIPAL
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 5. PASTA PRINTFLOW ====="

if (-not (Test-Path $Root)) {

    New-Item `
        -ItemType Directory `
        -Path $Root `
        -Force | Out-Null
}

Write-Host "[OK] $Root"

# ------------------------------------------------------------
# 6. PROJETO / GITHUB
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 6. PROJETO PRINTFLOW ====="

if (-not (Test-Path "$Projeto\.git")) {

    Write-Host "Projeto nao encontrado neste computador."
    Write-Host "Baixando versao oficial do GitHub..."
    Write-Host ""

    if (Test-Path $Projeto) {

        $conteudoExistente = Get-ChildItem `
            $Projeto `
            -Force `
            -ErrorAction SilentlyContinue

        if ($conteudoExistente) {

            $data = Get-Date -Format "yyyyMMdd-HHmmss"

            $destino = `
                "C:\PRINTFLOW\printflow-ai-ANTIGO-$data"

            Write-Host "Existe uma pasta sem Git."
            Write-Host "Movendo para:"
            Write-Host $destino

            Move-Item `
                $Projeto `
                $destino `
                -Force
        }
    }

    Set-Location $Root

    # CMD evita o falso NativeCommandError do PowerShell
    $gitClone = Start-Process `
        -FilePath "git.exe" `
        -ArgumentList "clone", $Repo, $Projeto `
        -WorkingDirectory $Root `
        -Wait `
        -NoNewWindow `
        -PassThru

    if ($gitClone.ExitCode -ne 0) {

        Parar-PrintFlow `
            "Nao foi possivel baixar o PRINTFLOW do GitHub."

    }
}

Write-Host "[OK] Repositorio encontrado"

Set-Location $Projeto

# ------------------------------------------------------------
# 7. SEGURANCA GIT
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 7. SEGURANCA DO REPOSITORIO ====="

$alteracoes = git status --porcelain

if ($alteracoes) {

    Write-Host ""
    Write-Host "[ATENCAO] Existem alteracoes locais."
    Write-Host ""
    git status -sb
    Write-Host ""
    Write-Host "Por seguranca o inicializador NAO fara pull."
    Write-Host "Nada sera apagado."

}
else {

    Write-Host "[OK] Repositorio local limpo"

    Write-Host ""
    Write-Host "Buscando atualizacoes..."

    $gitFetch = Start-Process `
        -FilePath "git.exe" `
        -ArgumentList "fetch", "origin" `
        -WorkingDirectory $Projeto `
        -Wait `
        -NoNewWindow `
        -PassThru

    if ($gitFetch.ExitCode -ne 0) {

        Parar-PrintFlow `
            "Falha ao consultar o GitHub."

    }

    Write-Host "Atualizando main..."

    $gitPull = Start-Process `
        -FilePath "git.exe" `
        -ArgumentList "pull", "--ff-only", "origin", "main" `
        -WorkingDirectory $Projeto `
        -Wait `
        -NoNewWindow `
        -PassThru

    if ($gitPull.ExitCode -ne 0) {

        Parar-PrintFlow `
            "Nao foi possivel atualizar a main automaticamente."

    }

    Write-Host "[OK] Projeto atualizado"
}

# ------------------------------------------------------------
# 8. COMMIT ATUAL
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 8. VERSAO ATUAL ====="

git status -sb
git log -1 --oneline

# ------------------------------------------------------------
# 9. AMBIENTE VIRTUAL
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 9. AMBIENTE PYTHON ====="

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {

    Write-Host ".venv nao encontrado."
    Write-Host "Criando ambiente virtual..."

    py -3.14 -m venv .venv

    if ($LASTEXITCODE -ne 0) {

        Parar-PrintFlow `
            "Nao foi possivel criar o ambiente virtual."

    }
}

& ".\.venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "Python utilizado pelo PRINTFLOW:"

python -c "import sys; print(sys.executable)"

# ------------------------------------------------------------
# 10. PIP
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 10. PIP ====="

python -m pip install `
    --upgrade pip `
    --disable-pip-version-check `
    -q

# ------------------------------------------------------------
# 11. DEPENDENCIAS
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 11. DEPENDENCIAS ====="

$HashFile = ".\.venv\.printflow-requirements.hash"

$arquivosReq = @(
    ".\requirements.txt",
    ".\requirements-dev.txt",
    ".\agent\python\requirements.txt"
)

$hashAtual = ""

foreach ($arquivo in $arquivosReq) {

    if (Test-Path $arquivo) {

        $hash = (
            Get-FileHash `
                $arquivo `
                -Algorithm SHA256
        ).Hash

        $hashAtual += $hash
    }
}

$hashAnterior = ""

if (Test-Path $HashFile) {

    $hashAnterior = Get-Content `
        $HashFile `
        -Raw
}

if ($hashAtual -ne $hashAnterior) {

    Write-Host "Dependencias novas ou alteradas."
    Write-Host "Atualizando ambiente..."

    python -m pip install `
        -r requirements-dev.txt

    if ($LASTEXITCODE -ne 0) {

        Parar-PrintFlow `
            "Falha ao instalar dependencias."

    }

    Set-Content `
        -Path $HashFile `
        -Value $hashAtual `
        -Encoding ASCII

    Write-Host "[OK] Dependencias atualizadas"

}
else {

    Write-Host "[OK] Dependencias ja atualizadas"

}

# ------------------------------------------------------------
# 12. EXTENSAO PYTHON VS CODE
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 12. VS CODE PYTHON ====="

if (Get-Command code -ErrorAction SilentlyContinue) {

    $pythonExtension = `
        code --list-extensions |
        Select-String "^ms-python.python$"

    if (-not $pythonExtension) {

        Write-Host "Instalando extensao Python..."

        code --install-extension `
            ms-python.python
    }

    Write-Host "[OK] Extensao Python"

}

# ------------------------------------------------------------
# 13. VALIDACAO PYSNMP
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 13. MOTOR SNMP ====="

python -c "import pysnmp; print('PySNMP:', pysnmp.__version__)"

if ($LASTEXITCODE -ne 0) {

    Parar-PrintFlow `
        "PySNMP nao esta disponivel."

}

# ------------------------------------------------------------
# 14. TESTES PRINTFLOW
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 14. TESTES PRINTFLOW ====="

# Pasta TEMP exclusiva do PRINTFLOW para evitar erros de permissao do Windows
$TempPrintFlow = "C:\PRINTFLOW\TEMP-PYTEST"

if (-not (Test-Path $TempPrintFlow)) {
    New-Item -ItemType Directory -Path $TempPrintFlow -Force | Out-Null
}

$env:TEMP = $TempPrintFlow
$env:TMP  = $TempPrintFlow

Write-Host "[OK] TEMP de testes: $TempPrintFlow"

python -m pytest -q --basetemp="$TempPrintFlow\pytest" -p no:cacheprovider

if ($LASTEXITCODE -ne 0) {

    Write-Host ""
    Write-Host "[ATENCAO] Existem testes com falha."
    Write-Host "Nao faremos nenhuma alteracao no Git."

    Read-Host "Pressione ENTER para continuar"

}
else {

    Write-Host ""
    Write-Host "[OK] TODOS OS TESTES PASSARAM"

}

# ------------------------------------------------------------
# 15. STATUS FINAL
# ------------------------------------------------------------

Write-Host ""
Write-Host "============================================================"
Write-Host " PRINTFLOW - AMBIENTE PRONTO"
Write-Host "============================================================"

Write-Host ""
Write-Host "Computador:"
$env:COMPUTERNAME

Write-Host ""
Write-Host "Projeto:"
Write-Host $Projeto

Write-Host ""
Write-Host "Branch:"
git branch --show-current

Write-Host ""
Write-Host "Commit:"
git log -1 --oneline

Write-Host ""
Write-Host "Git:"
git status -sb

Write-Host ""
Write-Host "============================================================"
Write-Host " NENHUM COMMIT FOI FEITO"
Write-Host " NENHUM PUSH FOI FEITO"
Write-Host "============================================================"

# ------------------------------------------------------------
# 16. ABRIR VS CODE
# ------------------------------------------------------------

if (Get-Command code -ErrorAction SilentlyContinue) {

    Write-Host ""

    $vscodeAberto = Get-Process "Code" -ErrorAction SilentlyContinue

    if ($vscodeAberto) {

        Write-Host "[OK] VS Code ja esta aberto"
        Write-Host "[INFO] Nao sera aberta uma segunda instancia"

    }
    else {

        Write-Host "Abrindo PRINTFLOW no VS Code..."

        Start-Process `
            -FilePath "code" `
            -ArgumentList "`"$Projeto`""
    }
}

Write-Host ""
Write-Host "PRINTFLOW PRONTO PARA PRODUZIR."
Write-Host ""

Read-Host "Pressione ENTER para fechar esta janela"




