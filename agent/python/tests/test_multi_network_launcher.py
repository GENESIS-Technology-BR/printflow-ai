from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_launcher_supports_multiple_manual_networks():
    launcher = (
        ROOT
        / "agent"
        / "windows"
        / "Start-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert "extra_networks" in launcher
    assert "[regex]::Split" in launcher
    assert "foreach ($extraNetwork in $extraNetworks)" in launcher
    assert '"--network"' in launcher


def test_launcher_keeps_legacy_network_compatibility():
    launcher = (
        ROOT
        / "agent"
        / "windows"
        / "Start-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert '"extra_network"' in launcher
    assert "[string]$savedConfig.extra_network" in launcher


def test_installer_saves_multiple_networks():
    installer = (
        ROOT
        / "agent"
        / "windows"
        / "Install-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert "extra_networks = $extraNetworks" in installer
    # A v0.3.2 pode formatar a atribuicao em multiplas linhas.
    # Validamos a semantica, nao a formatacao visual do PowerShell.
    assert "extra_network =" in installer
    assert "$extraNetworks -join" in installer
    assert (
        "Redes adicionais em CIDR separadas por virgula"
        in installer
    )