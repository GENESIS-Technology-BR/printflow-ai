@echo off
setlocal
cd /d "%~dp0"

rem TALVOA update-safe launcher
rem A elevacao ocorre antes de parar a instalacao residente, garantindo que
rem o executavel em ProgramData seja liberado antes da copia da nova build.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "$installer = '%~dp0Install-TALVOA-Agent.ps1'; $command = '& { Write-Host ''Preparando atualizacao segura do TALVOA...''; Write-Host ''Validando credencial antes de interromper o Agent existente...''; & ''' + $installer + ''' }'; Start-Process -FilePath '%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe' -Verb RunAs -ArgumentList '-NoLogo','-NoProfile','-NoExit','-ExecutionPolicy','Bypass','-Command',$command"

exit /b 0
