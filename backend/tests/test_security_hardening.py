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


def test_security_headers_and_restricted_cors_are_configured():
    main = source("backend/main.py")

    assert '"X-Content-Type-Options"' in main
    assert '"X-Frame-Options"' in main
    assert '"Referrer-Policy"' in main
    assert '"Permissions-Policy"' in main
    assert '"Strict-Transport-Security"' in main
    assert '"Content-Security-Policy"' in main

    assert 'allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]' in main
    assert '"Authorization"' in main
    assert '"Content-Type"' in main
    assert '"X-Recovery-Key"' in main
    assert 'allow_headers=["*"]' not in main
    assert 'allow_methods=["*"]' not in main


def test_login_has_basic_bruteforce_protection():
    router = source("backend/modules/auth/router.py")

    assert "LOGIN_ATTEMPT_LIMIT = 5" in router
    assert "LOGIN_ATTEMPT_WINDOW_SECONDS = 300" in router
    assert "_enforce_login_rate_limit" in router
    assert "HTTP_429_TOO_MANY_REQUESTS" in router
    assert "_clear_login_rate_limit" in router
