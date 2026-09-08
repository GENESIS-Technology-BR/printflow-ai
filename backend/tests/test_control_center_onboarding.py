from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.modules.control_center.schema import (
    ControlCenterClientCreate,
)


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (
        ROOT / path
    ).read_text(encoding="utf-8")


def test_onboarding_schema_accepts_valid_client():
    payload = ControlCenterClientCreate(
        company_name="Empresa Teste",
        responsible_name="Joao Silva",
        email="joao@example.com",
    )

    assert payload.company_name == "Empresa Teste"
    assert str(payload.email) == "joao@example.com"


def test_onboarding_schema_rejects_invalid_email():
    with pytest.raises(ValidationError):
        ControlCenterClientCreate(
            company_name="Empresa Teste",
            responsible_name="Joao Silva",
            email="email-invalido",
        )


def test_onboarding_endpoint_is_platform_admin_only():
    router = source(
        "backend/modules/control_center/router.py"
    )

    assert '"/clients"' in router
    assert "Depends(" in router
    assert "get_platform_admin" in router


def test_onboarding_creates_hashed_password():
    router = source(
        "backend/modules/control_center/router.py"
    )

    assert "secrets.token_urlsafe" in router
    assert (
        "password_hash=hash_password("
        in router
    )


def test_frontend_has_new_client_flow():
    component = source(
        "frontend/src/components/ControlCenter.tsx"
    )

    assert "+ Novo cliente" in component
    assert "Criar cliente" in component
    assert "Senha temporária" in component
    assert "Token do Agent" in component


def test_frontend_calls_admin_onboarding_api():
    api = source(
        "frontend/src/services/api.ts"
    )

    assert "createControlCenterClient" in api
    assert (
        '"/api/v1/control-center/clients"'
        in api
    )


def test_control_center_exposes_operational_onboarding_states():
    router = source(
        "backend/modules/control_center/router.py"
    )
    schema = source(
        "backend/modules/control_center/schema.py"
    )
    api = source(
        "frontend/src/services/api.ts"
    )
    component = source(
        "frontend/src/components/ControlCenter.tsx"
    )

    for state in (
        "awaiting_agent",
        "agent_connected",
        "pilot_active",
        "agent_attention",
        "inactive",
    ):
        assert state in router
        assert state in api

    assert "onboarding_state" in schema
    assert "Aguardando instalação" in component
    assert "Agent conectado" in component
    assert "Piloto ativo" in component
    assert "Requer atenção" in component


def test_pilot_readiness_contract_is_covered():
    control_center = source(
        "backend/modules/control_center/router.py"
    )
    alerts = source(
        "backend/modules/alerts/service.py"
    )
    reports = source(
        "backend/modules/usage/router.py"
    )
    workflow = source(
        ".github/workflows/build-agent-windows.yml"
    )

    assert "agent_last_seen" in control_center
    assert "active_printers" in control_center
    assert "Agent sem comunicação" in alerts
    assert '"/export.xlsx"' in reports
    assert '"/export.pdf"' in reports
    assert "Testar executável" in workflow
    assert "Montar pacote de teste" in workflow
