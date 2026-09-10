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


def test_security_dependencies_avoid_known_blockers():
    requirements = source("requirements.txt")

    assert "python-jose" not in requirements.lower()
    assert "PyJWT[crypto]" in requirements
    assert "pillow>=12.3" in requirements.lower()


def test_access_tokens_are_short_lived_and_require_security_claims():
    security_source = source(
        "backend/modules/auth/security.py"
    )

    assert "ACCESS_TOKEN_MINUTES = 60" in security_source
    assert '"iat"' in security_source
    assert '"jti"' in security_source
    for required_claim in (
        '"sub"',
        '"company_id"',
        '"session_version"',
        '"iat"',
        '"exp"',
        '"jti"',
    ):
        assert required_claim in security_source


def test_recovery_requires_strong_key_and_user_listing_is_off_by_default():
    router = source(
        "backend/modules/auth/router.py"
    )

    assert "len(key) < 32" in router
    assert "PRINTFLOW_ALLOW_RECOVERY_USER_LIST" in router
    assert '"false"' in router
    assert "Recurso indisponivel" in router


def test_logout_revokes_existing_sessions_by_version():
    model = source("backend/modules/auth/model.py")
    migrations = source("backend/app/database/migrations.py")
    dependencies = source(
        "backend/modules/auth/dependencies.py"
    )
    router = source(
        "backend/modules/auth/router.py"
    )
    security_source = source(
        "backend/modules/auth/security.py"
    )

    assert "session_version" in model
    assert "USER_SECURITY_COLUMNS" in migrations
    assert "token_session_version" in dependencies
    assert "Sessão revogada" in dependencies
    assert '@router.post("/logout")' in router
    assert "current_user.session_version += 1" in router
    assert '"session_version"' in security_source


def test_password_reset_revokes_previous_sessions():
    router = source(
        "backend/modules/auth/router.py"
    )

    reset_block = router.split(
        '"/recovery/reset-password"',
        1,
    )[1]

    assert "user.session_version += 1" in reset_block


def test_preview_token_uses_current_session_version():
    control_center = source(
        "backend/modules/control_center/router.py"
    )

    assert "user.session_version" in control_center
