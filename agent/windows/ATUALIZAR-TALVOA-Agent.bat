@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -NoExit -ExecutionPolicy Bypass -File "%~dp0Update-TALVOA-Agent.ps1"
if errorlevel 1 exit /b %errorlevel%

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Sync-TALVOA-Watchdog.ps1"
if errorlevel 1 exit /b %errorlevel%

echo.
echo TALVOA Agent atualizado e Watchdog sincronizado com sucesso.
pause
exit /b 0
