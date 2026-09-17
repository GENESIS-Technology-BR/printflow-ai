@echo off
setlocal
cd /d "%~dp0"

rem PRINTFLOW update-safe launcher
rem A elevacao ocorre antes de parar a instalacao residente, garantindo que
rem o executavel em ProgramData seja liberado antes da copia da nova build.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "$installer = '%~dp0Install-PRINTFLOW-Agent.ps1'; $command = '& { Write-Host ''Preparando atualizacao segura do PRINTFLOW...''; Stop-ScheduledTask -TaskName ''PRINTFLOW Agent Watchdog'' -ErrorAction SilentlyContinue; Stop-ScheduledTask -TaskName ''PRINTFLOW Agent'' -ErrorAction SilentlyContinue; Get-Process -Name ''PRINTFLOW-Agent'' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue; $limit=(Get-Date).AddSeconds(15); while ((Get-Process -Name ''PRINTFLOW-Agent'' -ErrorAction SilentlyContinue) -and ((Get-Date) -lt $limit)) { Start-Sleep -Milliseconds 500 }; if (Get-Process -Name ''PRINTFLOW-Agent'' -ErrorAction SilentlyContinue) { throw ''Nao foi possivel liberar o PRINTFLOW-Agent.exe para atualizacao.'' }; Write-Host ''[OK] Runtime anterior liberado.'' -ForegroundColor Green; & ''' + $installer + ''' }'; Start-Process -FilePath '%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe' -Verb RunAs -ArgumentList '-NoLogo','-NoProfile','-NoExit','-ExecutionPolicy','Bypass','-Command',$command"

exit /b 0
