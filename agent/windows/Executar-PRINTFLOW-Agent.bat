@echo off
setlocal EnableExtensions
title PRINTFLOW Agent

REM ============================================================
REM PRINTFLOW WINDOWS LAUNCHER
REM Trabalha sempre a partir da pasta onde este BAT esta salvo.
REM Compativel com caminhos contendo espacos e parenteses.
REM ============================================================

pushd "%~dp0" >nul 2>&1

if errorlevel 1 goto ERRO_PASTA

echo ============================================================
echo PRINTFLOW AGENT - TESTE NA REDE DO CLIENTE
echo ============================================================
echo.
echo Pasta do Agent:
echo %CD%
echo.

if exist "PRINTFLOW-Agent.exe" goto EXECUTAVEL_OK

echo ERRO: PRINTFLOW-Agent.exe nao foi encontrado.
echo.
echo Caminho atual:
echo %CD%
echo.
echo Mantenha estes arquivos juntos:
echo - PRINTFLOW-Agent.exe
echo - Executar-PRINTFLOW-Agent.bat
echo - README-TESTE.txt
echo.
pause
popd
exit /b 1

:EXECUTAVEL_OK
echo Executavel encontrado com sucesso.
echo.

set /p PRINTFLOW_AGENT_TOKEN=Digite ou cole o Token do Agent: 

if defined PRINTFLOW_AGENT_TOKEN goto TOKEN_OK

echo.
echo ERRO: O Token do Agent e obrigatorio.
echo.
pause
popd
exit /b 1

:TOKEN_OK
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

echo.
echo ============================================================
echo REDE ADICIONAL
echo ============================================================
echo.
set /p PRINTFLOW_EXTRA_NETWORK=Informe uma rede adicional em CIDR ou pressione ENTER para usar somente redes detectadas: 

if defined PRINTFLOW_EXTRA_NETWORK goto EXECUTAR_COM_REDE

echo.
echo Nenhuma rede adicional informada.
echo Executando somente descoberta automatica...
echo.

"PRINTFLOW-Agent.exe"
goto FINALIZAR

:EXECUTAR_COM_REDE
echo.
echo Rede adicional autorizada: %PRINTFLOW_EXTRA_NETWORK%
echo.

"PRINTFLOW-Agent.exe" --network "%PRINTFLOW_EXTRA_NETWORK%"

:FINALIZAR
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

popd
exit /b %AGENT_EXIT_CODE%

:ERRO_PASTA
echo.
echo ERRO: Nao foi possivel acessar a pasta do PRINTFLOW Agent.
echo.
pause
exit /b 1
