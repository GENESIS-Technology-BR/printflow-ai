@echo off
setlocal
start "TALVOA - Validacao do Build" "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NoExit -ExecutionPolicy Bypass -File "%~dp0Validar-TALVOA-Build.ps1"
exit /b 0
