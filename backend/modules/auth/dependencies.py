import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.model import User
from backend.modules.auth.security import decode_token

bearer = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada",
        )

    user = db.query(User).filter(User.id == user_id, User.active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
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
