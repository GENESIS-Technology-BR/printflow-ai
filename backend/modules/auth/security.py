import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

INSECURE_JWT_SECRET = "CHANGE-ME-IN-RENDER"
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60
PASSWORD_RESET_TOKEN_MINUTES = 15


def _secret_key() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()

    if not secret or secret == INSECURE_JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET seguro não configurado."
        )

    if len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET deve possuir pelo menos 32 caracteres."
        )

    return secret


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_b64, digest_b64 = encoded.split("$", 1)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def create_access_token(
    subject: str,
    company_id: int,
    session_version: int = 0,
    expires_minutes: int = ACCESS_TOKEN_MINUTES,
) -> str:
    issued_at = datetime.now(timezone.utc)
    expires = issued_at + timedelta(
        minutes=max(int(expires_minutes), 1)
    )
    payload = {
        "sub": subject,
        "company_id": company_id,
        "session_version": int(session_version),
        "iat": issued_at,
        "exp": expires,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _secret_key(),
            algorithms=[ALGORITHM],
            options={
                "require": [
                    "sub",
                    "company_id",
                    "session_version",
                    "iat",
                    "exp",
                    "jti",
                ],
            },
        )
    except InvalidTokenError as exc:
        raise ValueError("Token inválido ou expirado") from exc


def create_password_reset_token(
    subject: str,
    reset_version: int,
    expires_minutes: int = PASSWORD_RESET_TOKEN_MINUTES,
) -> str:
    issued_at = datetime.now(timezone.utc)
    expires = issued_at + timedelta(
        minutes=max(int(expires_minutes), 1)
    )
    payload = {
        "sub": subject,
        "purpose": "password_reset",
        "reset_version": int(reset_version),
        "iat": issued_at,
        "exp": expires,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(
        payload,
        _secret_key(),
        algorithm=ALGORITHM,
    )


def decode_password_reset_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            _secret_key(),
            algorithms=[ALGORITHM],
            options={
                "require": [
                    "sub",
                    "purpose",
                    "reset_version",
                    "iat",
                    "exp",
                    "jti",
                ],
            },
        )
    except InvalidTokenError as exc:
        raise ValueError(
            "Token de recuperação inválido ou expirado"
        ) from exc

    if payload.get("purpose") != "password_reset":
        raise ValueError(
            "Token de recuperação inválido"
        )

    return payload
