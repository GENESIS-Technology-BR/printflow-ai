from pathlib import Path

import pytest

from backend.modules.auth import security


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_jwt_secret_has_no_insecure_fallback(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError):
        security._secret_key()

    monkeypatch.setenv("JWT_SECRET", "short")

    with pytest.raises(RuntimeError):
        security._secret_key()

    strong_secret = "x" * 48
    monkeypatch.setenv("JWT_SECRET", strong_secret)

    assert security._secret_key() == strong_secret


def test_public_registration_is_disabled_by_default():
    router = source("backend/modules/auth/router.py")

    assert "PRINTFLOW_ALLOW_PUBLIC_REGISTRATION" in router
    assert '"false"' in router
    assert "Cadastro público desabilitado" in router


def test_authenticated_user_must_match_jwt_company():
    dependencies = source(
        "backend/modules/auth/dependencies.py"
    )

    assert 'payload["company_id"]' in dependencies
    assert "user.company_id" in dependencies
    assert "Sessão inválida para esta empresa" in dependencies
