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


def test_access_tokens_are_short_lived_and_require_security_claims(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(
        "JWT_SECRET",
        "security-test-secret-" + ("x" * 48),
    )

    token = security.create_access_token(
        subject="123",
        company_id=45,
        session_version=7,
    )
    payload = security.decode_token(token)

    assert security.ACCESS_TOKEN_MINUTES == 60
    assert payload["sub"] == "123"
    assert payload["company_id"] == 45
    assert payload["session_version"] == 7
    assert payload["iat"] is not None
    assert payload["exp"] is not None
    assert payload["jti"]

    ttl_seconds = int(payload["exp"]) - int(payload["iat"])
    assert 3590 <= ttl_seconds <= 3610


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


def test_auth_cookie_is_httponly_secure_in_production():
    router = source(
        "backend/modules/auth/router.py"
    )

    assert 'AUTH_COOKIE_NAME = "printflow_session"' in router
    assert "httponly=True" in router
    assert "secure=production" in router
    assert 'samesite="strict"' in router
    assert "_set_auth_cookie" in router
    assert "_clear_auth_cookie" in router


def test_frontend_is_ready_to_send_secure_session_cookie():
    api = source(
        "frontend/src/services/api.ts"
    )
    app = source(
        "frontend/src/App.tsx"
    )

    assert 'credentials: "include"' in api
    assert 'credentials: "include"' in app


def test_cookie_auth_fallback_and_csrf_contract():
    dependencies = source(
        "backend/modules/auth/dependencies.py"
    )
    main = source(
        "backend/main.py"
    )
    api = source(
        "frontend/src/services/api.ts"
    )
    app = source(
        "frontend/src/App.tsx"
    )

    assert 'AUTH_COOKIE_NAME = "printflow_session"' in dependencies
    assert "HTTPBearer(auto_error=False)" in dependencies
    assert "request.cookies.get" in dependencies
    assert 'CSRF_HEADER_NAME = "X-CSRF-Protection"' in dependencies
    assert 'CSRF_HEADER_VALUE = "1"' in dependencies
    assert "Proteção CSRF inválida" in dependencies

    assert '"X-CSRF-Protection"' in main
    assert '"X-CSRF-Protection": "1"' in api
    assert '"X-CSRF-Protection": "1"' in app


def test_frontend_no_longer_persists_primary_jwt_in_localstorage():
    api = source(
        "frontend/src/services/api.ts"
    )
    app = source(
        "frontend/src/App.tsx"
    )
    control_center = source(
        "frontend/src/components/ControlCenter.tsx"
    )

    assert 'localStorage.getItem("printflow_token")' not in api
    assert 'localStorage.setItem("printflow_token"' not in app
    assert 'localStorage.removeItem("printflow_token")' not in app

    assert '"printflow_preview_token"' in api
    assert '"printflow_preview_token"' in app
    assert '"printflow_preview_token"' in control_center

    assert "setAuthenticated(true)" in app
    assert 'api("/api/v1/auth/logout", { method: "POST" })' in app


def test_login_response_never_exposes_access_token():
    schema = source("backend/modules/auth/schema.py")
    router = source("backend/modules/auth/router.py")

    assert "class SessionResponse" in schema
    session_block = schema.split("class SessionResponse", 1)[1].split("class MeResponse", 1)[0]
    assert "access_token" not in session_block
    assert "response_model=SessionResponse" in router
    assert "return SessionResponse(" in router


def test_platform_admin_role_cannot_be_granted_by_environment_email():
    dependencies = source("backend/modules/auth/dependencies.py")
    admin_block = dependencies.split("def is_platform_admin", 1)[1].split("def get_platform_admin", 1)[0]

    assert 'user.role == "platform_admin"' in admin_block
    assert "PRINTFLOW_PLATFORM_ADMIN_EMAILS" not in admin_block


def test_security_gate_blocks_high_dependency_risk():
    workflow = source(".github/workflows/build-agent-windows.yml")

    assert "pip-audit -r requirements.txt" in workflow
    assert "npm audit --audit-level=high" in workflow
    assert "python -m pytest -q agent/python/tests backend/tests" in workflow
    assert "actions/checkout@v5" in workflow
    assert "actions/setup-python@v6" in workflow
    assert "actions/setup-node@v5" in workflow
    assert "actions/upload-artifact@v5" in workflow
