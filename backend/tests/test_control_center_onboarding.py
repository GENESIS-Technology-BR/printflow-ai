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
