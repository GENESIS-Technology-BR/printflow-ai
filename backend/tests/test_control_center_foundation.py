import os
from pathlib import Path
from types import SimpleNamespace

from backend.modules.auth.dependencies import (
    is_platform_admin,
)


ROOT = Path(__file__).resolve().parents[2]


def test_platform_admin_role_is_allowed(monkeypatch):
    monkeypatch.delenv(
        "PRINTFLOW_PLATFORM_ADMIN_EMAILS",
        raising=False,
    )

    user = SimpleNamespace(
        role="platform_admin",
        email="admin@example.com",
    )

    assert is_platform_admin(user) is True


def test_platform_admin_email_allowlist(monkeypatch):
    monkeypatch.setenv(
        "PRINTFLOW_PLATFORM_ADMIN_EMAILS",
        "administrador@printflow.com.br",
    )

    user = SimpleNamespace(
        role="admin",
        email="administrador@printflow.com.br",
    )

    assert is_platform_admin(user) is True


def test_regular_company_admin_is_not_platform_admin(
    monkeypatch,
):
    monkeypatch.delenv(
        "PRINTFLOW_PLATFORM_ADMIN_EMAILS",
        raising=False,
    )

    user = SimpleNamespace(
        role="admin",
        email="cliente@example.com",
    )

    assert is_platform_admin(user) is False


def test_control_center_endpoint_is_protected():
    source = (
        ROOT
        / "backend"
        / "modules"
        / "control_center"
        / "router.py"
    ).read_text(encoding="utf-8")

    assert "Depends(get_platform_admin)" in source
    assert 'prefix="/control-center"' in source


def test_control_center_frontend_is_role_restricted():
    source = (
        ROOT
        / "frontend"
        / "src"
        / "App.tsx"
    ).read_text(encoding="utf-8")

    assert (
        'profile?.role === "platform_admin"'
        in source
    )

    assert "<ControlCenter />" in source


def test_agent_monitor_explains_real_intervals():
    source = (
        ROOT
        / "frontend"
        / "src"
        / "components"
        / "AgentMonitor.tsx"
    ).read_text(encoding="utf-8")

    assert "Coleta do Agent a cada 5 min" in source
    assert "tela atualizada a cada 30 s" in source
