@echo off
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -NoExit -ExecutionPolicy Bypass -File "%~dp0Update-PRINTFLOW-Agent.ps1"