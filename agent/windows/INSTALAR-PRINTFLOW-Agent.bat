@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Process -FilePath '%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe' -Verb RunAs -ArgumentList '-NoLogo -NoProfile -NoExit -ExecutionPolicy Bypass -File ""%~dp0Install-PRINTFLOW-Agent.ps1""'"
exit /b 0
