from __future__ import annotations

from pathlib import Path


def test_windows_installer_has_autorecovery_policy() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "windows"
        / "Install-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert "-AtStartup" in script
    assert '-UserId "SYSTEM"' in script
    assert "-RestartCount 10" in script
    assert "-RestartInterval (New-TimeSpan -Minutes 1)" in script
    assert "-MultipleInstances IgnoreNew" in script


def test_windows_installer_registers_watchdog() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "windows"
        / "Install-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert "PRINTFLOW Agent Watchdog" in script
    assert "Watchdog-PRINTFLOW-Agent.ps1" in script
    assert "-RepetitionInterval (New-TimeSpan -Minutes 15)" in script
