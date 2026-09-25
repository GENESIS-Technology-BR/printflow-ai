from __future__ import annotations

from pathlib import Path

import pytest

from backend.modules.auth.security import (
    create_password_reset_token,
    decode_password_reset_token,
)


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_password_reset_token_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "x" * 64)

    token = create_password_reset_token(
        "42",
        reset_version=7,
    )
    payload = decode_password_reset_token(token)

    assert payload["sub"] == "42"
    assert payload["purpose"] == "password_reset"
    assert payload["reset_version"] == 7
    assert payload["exp"] > payload["iat"]


def test_password_reset_token_rejects_tampering(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "y" * 64)

    token = create_password_reset_token("42", reset_version=1)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    with pytest.raises(ValueError):
        decode_password_reset_token(tampered)


def test_public_recovery_does_not_expose_reset_token() -> None:
    router = source("backend/modules/auth/router.py")

    public_block = router.split(
        '@router.post(\n    "/forgot-password"',
        1,
    )[1].split('@router.post("/reset-password")', 1)[0]

    assert "return PasswordResetRequestResponse(message=generic_message)" in public_block
    assert "reset_token=reset_token" not in public_block
    assert "Usuario nao encontrado" not in public_block
    assert "Se o e-mail estiver cadastrado" in public_block


def test_public_registration_is_not_exposed_in_login_ui() -> None:
    app = source("frontend/src/App.tsx")

    login_block = app.split("if (!authenticated)", 1)[1].split(
        "const previewCompany",
        1,
    )[0]

    assert "Criar conta" not in login_block
    assert "Esqueceu sua senha?" in login_block
    assert "reset-password" in app
