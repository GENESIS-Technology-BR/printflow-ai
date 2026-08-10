@echo off
setlocal EnableExtensions
title PRINTFLOW Agent

REM ============================================================
REM Sempre trabalha a partir da pasta onde este BAT esta salvo.
REM Isso evita erro quando executado como Administrador.
REM ============================================================
cd /d "%~dp0"

echo ============================================================
echo PRINTFLOW AGENT - TESTE NA REDE DO CLIENTE
echo ============================================================
echo.
echo Pasta do Agent:
echo %CD%
echo.

if not exist "%~dp0PRINTFLOW-Agent.exe" --network 10.2.0.0/24 (
    echo ERRO: PRINTFLOW-Agent.exe nao foi encontrado.
    echo.
    echo Caminho procurado:
    echo %~dp0PRINTFLOW-Agent.exe
    echo.
    echo Mantenha estes arquivos juntos:
    echo - PRINTFLOW-Agent.exe
    echo - Executar-PRINTFLOW-Agent.bat
    echo - README-TESTE.txt
    echo.
    pause
    exit /b 1
)

echo Executavel encontrado com sucesso.
echo.

set /p PRINTFLOW_AGENT_TOKEN=Digite ou cole o Token do Agent: 

if "%PRINTFLOW_AGENT_TOKEN%"=="" (
    echo.
    echo ERRO: O Token do Agent e obrigatorio.
    pause
    exit /b 1
)

set "PRINTFLOW_API_URL=https://printflow-api-genesis.onrender.com"
set "PRINTFLOW_AGENT_NAME=PRINTFLOW Agent Windows"
set "PRINTFLOW_SCAN_INTERVAL=900"
set "PRINTFLOW_MAXIMUM_HOSTS=1024"
set "PRINTFLOW_SNMP_COMMUNITY=public"
set "PRINTFLOW_NETWORK_TIMEOUT=0.40"
set "PRINTFLOW_SNMP_TIMEOUT=1.50"
set "PRINTFLOW_SNMP_RETRIES=1"

echo.
echo ============================================================
echo INICIANDO PRINTFLOW AGENT
echo ============================================================
echo API: %PRINTFLOW_API_URL%
echo.
echo Nao feche esta janela durante o teste.
echo.

"%~dp0PRINTFLOW-Agent.exe"

set "AGENT_EXIT_CODE=%ERRORLEVEL%"

echo.
echo ============================================================
echo PRINTFLOW AGENT FINALIZADO
echo ============================================================
echo Codigo de saida: %AGENT_EXIT_CODE%
echo.
echo Verifique:
echo 1. A pasta output
echo 2. A pasta logs
echo 3. O Dashboard do PRINTFLOW
echo.

pause
exit /b %AGENT_EXIT_CODE%
