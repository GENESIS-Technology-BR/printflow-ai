@echo off
setlocal
title PRINTFLOW Agent

echo ============================================================
echo PRINTFLOW AGENT - TESTE NA REDE DO CLIENTE
echo ============================================================
echo.

if not exist "PRINTFLOW-Agent.exe" (
    echo ERRO: PRINTFLOW-Agent.exe nao foi encontrado.
    echo Mantenha este arquivo na mesma pasta do executavel.
    pause
    exit /b 1
)

set /p PRINTFLOW_AGENT_TOKEN=Digite o Token do Agent exibido no Dashboard: 

if "%PRINTFLOW_AGENT_TOKEN%"=="" (
    echo.
    echo ERRO: O Token do Agent e obrigatorio.
    pause
    exit /b 1
)

set PRINTFLOW_API_URL=https://printflow-api-genesis.onrender.com
set PRINTFLOW_AGENT_NAME=PRINTFLOW Agent Windows
set PRINTFLOW_SCAN_INTERVAL=900
set PRINTFLOW_MAXIMUM_HOSTS=1024
set PRINTFLOW_SNMP_COMMUNITY=public
set PRINTFLOW_NETWORK_TIMEOUT=0.40
set PRINTFLOW_SNMP_TIMEOUT=1.50
set PRINTFLOW_SNMP_RETRIES=1

echo.
echo Iniciando descoberta automatica...
echo Nao feche esta janela durante o teste.
echo.

PRINTFLOW-Agent.exe

echo.
echo ============================================================
echo TESTE FINALIZADO
echo ============================================================
echo.
echo Verifique:
echo 1. A pasta output
echo 2. A pasta logs
echo 3. O Dashboard do PRINTFLOW
echo.
pause
