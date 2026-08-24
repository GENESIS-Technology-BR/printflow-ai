# ============================================================
# PRINTFLOW - BOOTSTRAP WINDOWS
# Genesis Technology
#
# Objetivo:
# Preparar um computador novo para desenvolvimento PRINTFLOW
# usando somente ferramentas gratuitas.
# ============================================================

$ErrorActionPreference = "Continue"

$Root = "C:\PRINTFLOW"
$Projeto = "C:\PRINTFLOW\printflow-ai"
$Repo = "https://github.com/GENESIS-Technology-BR/printflow-ai.git"
$InicializadorRepo = "tools\windows\INICIAR-PRINTFLOW.ps1"
$InicializadorLocal = "C:\PRINTFLOW\INICIAR-PRINTFLOW.ps1"

Clear-Host

Write-Host ""
Write-Host "============================================================"
Write-Host " PRINTFLOW - BOOTSTRAP WINDOWS"
Write-Host "============================================================"
Write-Host ""

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

function Falha {

    param(
        [string]$Mensagem
    )

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "[ERRO] $Mensagem"
    Write-Host "============================================================"
    Write-Host ""

    Read-Host "Pressione ENTER para fechar"
    exit 1
}

# ------------------------------------------------------------
# 1. WINGET
# ------------------------------------------------------------

Write-Host "===== 1. WINGET ====="

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {

    Falha "Winget nao encontrado. Atualize o App Installer."

}

Write-Host "[OK] Winget"

# ------------------------------------------------------------
# 2. GIT
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 2. GIT ====="

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {

    Write-Host "Instalando Git..."

    winget install `
        --id Git.Git `
        --exact `
        --silent `
        --accept-package-agreements `
        --accept-source-agreements

    Atualizar-Path
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {

    Falha "Git nao ficou disponivel. Reinicie o PowerShell."

}

git --version

# ------------------------------------------------------------
# 3. VS CODE
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 3. VS CODE ====="

if (-not (Get-Command code -ErrorAction SilentlyContinue)) {

    Write-Host "Instalando VS Code..."

    winget install `
        --id Microsoft.VisualStudioCode `
        --exact `
        --silent `
        --accept-package-agreements `
        --accept-source-agreements

    Atualizar-Path
}

if (Get-Command code -ErrorAction SilentlyContinue) {
    Write-Host "[OK] VS Code"
}
else {
    Write-Host "[AVISO] VS Code instalado, mas pode exigir novo PowerShell."
}

# ------------------------------------------------------------
# 4. PYTHON
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 4. PYTHON ====="

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {

    Write-Host "Instalando Python 3.14..."

    winget install `
        --id Python.Python.3.14 `
        --exact `
        --silent `
        --accept-package-agreements `
        --accept-source-agreements

    Atualizar-Path
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {

    Falha "Python nao ficou disponivel. Reinicie o PowerShell."

}

py --version

# ------------------------------------------------------------
# 5. PASTA PRINCIPAL
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 5. PASTA PRINTFLOW ====="

New-Item `
    -ItemType Directory `
    -Path $Root `
    -Force | Out-Null

Write-Host "[OK] $Root"

# ------------------------------------------------------------
# 6. REPOSITORIO
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 6. REPOSITORIO ====="

if (-not (Test-Path "$Projeto\.git")) {

    Write-Host "Projeto nao encontrado."
    Write-Host "Baixando do GitHub..."

    if (Test-Path $Projeto) {

        $conteudo = Get-ChildItem `
            $Projeto `
            -Force `
            -ErrorAction SilentlyContinue

        if ($conteudo) {

            $data = Get-Date -Format "yyyyMMdd-HHmmss"

            $antigo = `
                "C:\PRINTFLOW\printflow-ai-ANTIGO-$data"

            Write-Host "Pasta existente sem Git sera preservada em:"
            Write-Host $antigo

            Move-Item `
                $Projeto `
                $antigo `
                -Force
        }
    }

    $gitClone = Start-Process `
        -FilePath "git.exe" `
        -ArgumentList "clone", $Repo, $Projeto `
        -WorkingDirectory $Root `
        -Wait `
        -NoNewWindow `
        -PassThru

    if ($gitClone.ExitCode -ne 0) {

        Falha "Nao foi possivel baixar o PRINTFLOW."

    }
}

Write-Host "[OK] Repositorio encontrado"

Set-Location $Projeto

# ------------------------------------------------------------
# 7. SINCRONIZACAO SEGURA
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 7. SINCRONIZACAO ====="

$alteracoes = git status --porcelain

if ($alteracoes) {

    Write-Host "[ATENCAO] Existem alteracoes locais."
    Write-Host "O Bootstrap NAO fara pull."
    git status -sb

}
else {

    $fetch = Start-Process `
        -FilePath "git.exe" `
        -ArgumentList "fetch", "origin" `
        -WorkingDirectory $Projeto `
        -Wait `
        -NoNewWindow `
        -PassThru

    if ($fetch.ExitCode -ne 0) {

        Falha "Falha ao consultar GitHub."

    }

    $pull = Start-Process `
        -FilePath "git.exe" `
        -ArgumentList "pull", "--ff-only", "origin", "main" `
        -WorkingDirectory $Projeto `
        -Wait `
        -NoNewWindow `
        -PassThru

    if ($pull.ExitCode -ne 0) {

        Falha "Nao foi possivel atualizar main."

    }

    Write-Host "[OK] Projeto sincronizado"
}

# ------------------------------------------------------------
# 8. COPIAR INICIALIZADOR OFICIAL
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 8. INICIALIZADOR OFICIAL ====="

$fonte = Join-Path $Projeto $InicializadorRepo

if (-not (Test-Path $fonte)) {

    Falha "Inicializador oficial nao encontrado dentro do projeto."

}

Copy-Item `
    $fonte `
    $InicializadorLocal `
    -Force

Write-Host "[OK] Inicializador instalado em:"
Write-Host $InicializadorLocal

# ------------------------------------------------------------
# 9. EXECUTAR INICIALIZADOR OFICIAL
# ------------------------------------------------------------

Write-Host ""
Write-Host "===== 9. PREPARANDO AMBIENTE ====="

Set-ExecutionPolicy `
    -Scope Process `
    -ExecutionPolicy Bypass `
    -Force

& $InicializadorLocal

Write-Host ""
Write-Host "============================================================"
Write-Host " BOOTSTRAP PRINTFLOW FINALIZADO"
Write-Host "============================================================"
