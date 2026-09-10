import os
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.model import User
from backend.modules.auth.security import decode_token

AUTH_COOKIE_NAME = "printflow_session"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER_NAME = "X-CSRF-Protection"
CSRF_HEADER_VALUE = "1"

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    bearer_token = (
        credentials.credentials
        if credentials is not None
        else None
    )
    cookie_token = request.cookies.get(
        AUTH_COOKIE_NAME
    )
    token = bearer_token or cookie_token

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão não informada",
        )

    if (
        bearer_token is None
        and cookie_token is not None
        and request.method.upper() not in SAFE_METHODS
        and request.headers.get(CSRF_HEADER_NAME) != CSRF_HEADER_VALUE
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Proteção CSRF inválida",
        )

    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
        token_company_id = int(payload["company_id"])
        token_session_version = int(
            payload["session_version"]
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada",
        )

    user = db.query(User).filter(User.id == user_id, User.active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    if int(user.company_id) != token_company_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida para esta empresa",
        )

    if int(user.session_version) != token_session_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão revogada",
        )

    return user



def is_platform_admin(user: User) -> bool:
    configured = {
        item.strip().lower()
        for item in os.getenv(
            "PRINTFLOW_PLATFORM_ADMIN_EMAILS",
            "",
        ).split(",")
        if item.strip()
    }

    return (
        user.role == "platform_admin"
        or user.email.strip().lower() in configured
    )


def get_platform_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not is_platform_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Acesso restrito ao administrador da plataforma",
        )

    return current_user
