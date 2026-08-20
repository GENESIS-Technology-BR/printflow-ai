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
    assert "$plainToken.Length -lt 10" in installer
    assert "Set-Clipboard -Value \"\"" in installer
