from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_updater_preserves_existing_configuration():
    updater = (
        ROOT / "agent" / "windows" / "Update-TALVOA-Agent.ps1"
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
        ROOT / "agent" / "windows" / "Update-TALVOA-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert '"TALVOA\\Backups"' in updater
    assert "Restore-TalvoaBackup" in updater
    assert "$backupReady" in updater
    assert "ROLLBACK TALVOA" in updater
    assert "A versao anterior foi restaurada" in updater


def test_updater_restores_system_resident_agent():
    updater = (
        ROOT / "agent" / "windows" / "Update-TALVOA-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert "Register-TalvoaTask" in updater
    assert "New-ScheduledTaskPrincipal" in updater
    assert '-UserId "SYSTEM"' in updater
    assert "-LogonType ServiceAccount" in updater
    assert "-RunLevel Highest" in updater
    assert "New-ScheduledTaskTrigger" in updater
    assert "-AtStartup" in updater
    assert "Start-AndValidateTalvoaAgent" in updater
    assert "-RestartCount 10" in updater
    assert "-RestartInterval (New-TimeSpan -Minutes 1)" in updater


def test_two_click_updater_is_safe():
    batch = (
        ROOT / "agent" / "windows" / "ATUALIZAR-TALVOA-Agent.bat"
    ).read_text(encoding="utf-8")

    assert "%~dp0" in batch
    assert "Update-TALVOA-Agent.ps1" in batch
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
        / "Validar-TALVOA-Build.ps1"
    ).read_text(encoding="utf-8")

    assert (
        "Copy-Item "
        "agent/windows/ATUALIZAR-TALVOA-Agent.bat "
        "package/"
    ) in workflow

    assert (
        "Copy-Item "
        "agent/windows/Update-TALVOA-Agent.ps1 "
        "package/"
    ) in workflow

    assert '"ATUALIZAR-TALVOA-Agent.bat"' in workflow
    assert '"Update-TALVOA-Agent.ps1"' in workflow

    assert '"ATUALIZAR-TALVOA-Agent.bat"' in validator
    assert '"Update-TALVOA-Agent.ps1"' in validator
