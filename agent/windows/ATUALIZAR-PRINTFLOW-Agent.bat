@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Update-PRINTFLOW-Agent.ps1"
if errorlevel 1 exit /b %errorlevel%

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Sync-PRINTFLOW-Watchdog.ps1"
if errorlevel 1 exit /b %errorlevel%

echo.
echo PRINTFLOW Agent atualizado e Watchdog sincronizado com sucesso.
pause
exit /b 0
