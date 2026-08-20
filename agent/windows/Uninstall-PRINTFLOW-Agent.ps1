$ErrorActionPreference = "Stop"
$taskName = "PRINTFLOW Agent"
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
Write-Host "Tarefa automatica do PRINTFLOW Agent removida." -ForegroundColor Green
