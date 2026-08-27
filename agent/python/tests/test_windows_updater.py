from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_updater_preserves_existing_configuration():
    updater = (
        ROOT / "agent" / "windows" / "Update-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert "encrypted_token_machine" in updater
    assert "$tokenBefore" in updater
    assert "$tokenAfter" in updater
    assert "$networksBefore" in updater
    assert "$networksAfter" in updater

    assert "Get-Clipboard" not in updater

    assert "$tokenAfter -ne $tokenBefore" in updater
    assert "$networksAfter -ne $networksBefore" in updater


def test_updater_has_backup_and_rollback():
    updater = (
        ROOT / "agent" / "windows" / "Update-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert '"PRINTFLOW\\Backups"' in updater
    assert "Restore-PrintflowBackup" in updater
    assert "$backupReady" in updater
    assert "ROLLBACK PRINTFLOW" in updater
    assert "A versao anterior foi restaurada" in updater


def test_updater_restores_system_resident_agent():
    updater = (
        ROOT / "agent" / "windows" / "Update-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert "Register-PrintflowTask" in updater
    assert "New-ScheduledTaskPrincipal" in updater
    assert '-UserId "SYSTEM"' in updater
    assert "-LogonType ServiceAccount" in updater
    assert "-RunLevel Highest" in updater
    assert "New-ScheduledTaskTrigger" in updater
    assert "-AtStartup" in updater
    assert "Start-AndValidatePrintflowAgent" in updater


def test_two_click_updater_is_safe():
    batch = (
        ROOT / "agent" / "windows" / "ATUALIZAR-PRINTFLOW-Agent.bat"
    ).read_text(encoding="utf-8")

    assert "%~dp0" in batch
    assert "Update-PRINTFLOW-Agent.ps1" in batch
    assert "-NoExit" in batch

    assert "token" not in batch.lower()
    assert "set /p" not in batch.lower()


def test_updater_is_in_build_and_validator():
    workflow = (
        ROOT
        / ".github"
        / "workflows"
        / "build-agent-windows.yml"
    ).read_text(encoding="utf-8")

    validator = (
        ROOT
        / "agent"
        / "windows"
        / "Validar-PRINTFLOW-Build.ps1"
    ).read_text(encoding="utf-8")

    assert (
        "Copy-Item "
        "agent/windows/ATUALIZAR-PRINTFLOW-Agent.bat "
        "package/"
    ) in workflow

    assert (
        "Copy-Item "
        "agent/windows/Update-PRINTFLOW-Agent.ps1 "
        "package/"
    ) in workflow

    assert '"ATUALIZAR-PRINTFLOW-Agent.bat"' in workflow
    assert '"Update-PRINTFLOW-Agent.ps1"' in workflow

    assert '"ATUALIZAR-PRINTFLOW-Agent.bat"' in validator
    assert '"Update-PRINTFLOW-Agent.ps1"' in validator
