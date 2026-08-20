@echo off
setlocal
cd /d "%~dp0"
start "PRINTFLOW Agent - Instalacao" "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NoExit -ExecutionPolicy Bypass -File "%~dp0Install-PRINTFLOW-Agent.ps1"
exit /b 0
