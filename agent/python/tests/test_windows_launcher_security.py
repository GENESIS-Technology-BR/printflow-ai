from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_launcher_uses_hidden_token_prompt():
    launcher = (
        ROOT / "agent" / "windows" / "Start-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert "Read-Host \"Digite ou cole o Token do Agent\" -AsSecureString" in launcher
    assert "$env:PRINTFLOW_AGENT_TOKEN = $null" in launcher


def test_batch_file_does_not_echo_or_read_token():
    batch = (
        ROOT / "agent" / "windows" / "Executar-PRINTFLOW-Agent.bat"
    ).read_text(encoding="utf-8")

    assert "set /p PRINTFLOW_AGENT_TOKEN" not in batch
    assert "Start-PRINTFLOW-Agent.ps1" in batch


def test_installer_reads_clipboard_and_validates_token():
    installer = (
        ROOT / "agent" / "windows" / "Install-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert "Get-Clipboard -Raw" in installer
    assert 'Read-Host "Depois pressione ENTER para continuar"' not in installer
    assert "^[A-Za-z0-9_-]{43}$" in installer
    assert "nao copie o token de sessao" in installer
    assert "printers/agent/heartbeat" in installer
    assert "Set-Clipboard -Value \"[PRINTFLOW token protegido]\"" in installer
    assert "-MultipleInstances IgnoreNew" in installer
    assert "Unregister-ScheduledTask" in installer
    assert "-RepetitionInterval (New-TimeSpan -Minutes 15)" in installer
    assert "-ExecutionTimeLimit (New-TimeSpan -Minutes 10)" in installer
    assert '-WindowStyle Hidden' in installer
    assert '-Daemon' not in installer


def test_launcher_rejects_clipboard_marker_as_token():
    launcher = (
        ROOT / "agent" / "windows" / "Start-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert "^[A-Za-z0-9_-]{43}$" in launcher
    assert "encrypted_token_machine" not in launcher


def test_two_click_installer_keeps_window_open():
    batch = (
        ROOT / "agent" / "windows" / "INSTALAR-PRINTFLOW-Agent.bat"
    ).read_text(encoding="utf-8")
    installer = (
        ROOT / "agent" / "windows" / "Install-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert "%~dp0" in batch
    assert "-NoExit" in batch
    assert "-Verb RunAs" in batch
    assert "-Verb RunAs" in installer
    assert "Install-PRINTFLOW-Agent.ps1" in batch
    assert "set /p" not in batch.lower()


def test_build_validation_is_available_in_two_click_mode():
    batch = (
        ROOT / "agent" / "windows" / "VALIDAR-PRINTFLOW-Build.bat"
    ).read_text(encoding="utf-8")
    validator = (
        ROOT / "agent" / "windows" / "Validar-PRINTFLOW-Build.ps1"
    ).read_text(encoding="utf-8")

    assert "%~dp0" in batch
    assert "-NoExit" in batch
    assert "Validar-PRINTFLOW-Build.ps1" in batch
    assert "RESULTADO-VALIDACAO.txt" in validator
    assert "Get-FileHash" in validator
    assert "PRINTFLOW-Agent.exe" in validator
    assert "--help" in validator
    assert 'Get-ScheduledTask -TaskName "PRINTFLOW Agent"' in validator
    assert '$task.State -ne "Queued"' in validator
    assert '$taskInfo.LastTaskResult -eq 0' in validator
