from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_version_has_single_source():
    version_file = (
        ROOT / "agent" / "python" / "version.py"
    ).read_text(encoding="utf-8")

    settings = (
        ROOT / "agent" / "python" / "config" / "settings.py"
    ).read_text(encoding="utf-8")

    assert 'AGENT_VERSION = "0.3.1"' in version_file
    assert "from version import AGENT_VERSION" in settings
    assert '"0.3.1"' not in settings


def test_installer_reads_version_from_build_metadata():
    installer = (
        ROOT / "agent" / "windows" / "Install-PRINTFLOW-Agent.ps1"
    ).read_text(encoding="utf-8")

    assert 'BUILD-VALIDATION.txt' in installer
    assert '$agentVersion' in installer
    assert 'agent_version = $agentVersion' in installer
    assert 'agent_version = "0.3.1"' not in installer


def test_workflow_does_not_have_manual_build_number():
    workflow = (
        ROOT / ".github" / "workflows" / "build-agent-windows.yml"
    ).read_text(encoding="utf-8")

    assert 'PRINTFLOW_BUILD_NUMBER:' not in workflow
    assert 'Build: ${{ github.run_number }}' in workflow
    assert 'Build-${{ github.run_number }}' in workflow


def test_workflow_reads_agent_version_from_version_module():
    workflow = (
        ROOT / ".github" / "workflows" / "build-agent-windows.yml"
    ).read_text(encoding="utf-8")

    assert "from version import AGENT_VERSION" in workflow
    assert "Version: $agentVersion" in workflow
    assert "PRINTFLOW_AGENT_VERSION:" not in workflow


def test_validator_is_dynamic():
    validator = (
        ROOT / "agent" / "windows" / "Validar-PRINTFLOW-Build.ps1"
    ).read_text(encoding="utf-8")

    assert "$buildNumber" in validator
    assert "$buildVersion" in validator
    assert "[long]$taskInfo.LastTaskResult" in validator