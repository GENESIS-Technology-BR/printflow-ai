@echo off
setlocal EnableExtensions
title TALVOA Agent

pushd "%~dp0" >nul 2>&1
if errorlevel 1 goto ERRO_PASTA

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-TALVOA-Agent.ps1"
set "AGENT_EXIT_CODE=%ERRORLEVEL%"

popd
exit /b %AGENT_EXIT_CODE%

:ERRO_PASTA
echo ERRO: Nao foi possivel acessar a pasta do TALVOA Agent.
pause
exit /b 1
