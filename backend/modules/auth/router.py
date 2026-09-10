import hmac
import os
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user, is_platform_admin
from backend.modules.auth.model import User
from backend.modules.auth.schema import (
    LoginRequest,
    MeResponse,
    RegisterRequest,
    TokenResponse,
)
from backend.modules.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.modules.companies.model import Company

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _recovery_key() -> str:
    key = os.getenv(
        "PRINTFLOW_RECOVERY_KEY",
        "",
    ).strip()

    if len(key) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recuperacao desabilitada",
        )

    return key


LOGIN_ATTEMPT_WINDOW_SECONDS = 300
LOGIN_ATTEMPT_LIMIT = 5
_login_attempts: dict[str, deque[float]] = defaultdict(deque)


def _login_rate_limit_key(
    request: Request,
    email: str,
) -> str:
    client_ip = (
        request.client.host
        if request.client
        else "unknown"
    )
    return f"{client_ip}:{email.lower().strip()}"


def _enforce_login_rate_limit(
    request: Request,
    email: str,
) -> None:
    now = time.monotonic()
    key = _login_rate_limit_key(request, email)
    bucket = _login_attempts[key]

    while (
        bucket
        and now - bucket[0]
        > LOGIN_ATTEMPT_WINDOW_SECONDS
    ):
        bucket.popleft()

    if len(bucket) >= LOGIN_ATTEMPT_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente em alguns minutos.",
        )

    bucket.append(now)


def _clear_login_rate_limit(
    request: Request,
    email: str,
) -> None:
    _login_attempts.pop(
        _login_rate_limit_key(request, email),
        None,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    allow_public_registration = os.getenv(
        "PRINTFLOW_ALLOW_PUBLIC_REGISTRATION",
        "false",
    ).strip().lower() in {"1", "true", "yes"}

    if not allow_public_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cadastro público desabilitado",
        )

    email = payload.email.lower().strip()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=409,
            detail="E-mail já cadastrado",
        )

    company = Company(
        name=payload.company_name.strip()
    )

    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        name=payload.user_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="admin",
    )

    db.add(user)
    db.commit()

    db.refresh(user)
    db.refresh(company)

    return TokenResponse(
        access_token=create_access_token(
            str(user.id),
            company.id,
            user.session_version,
        ),
        user_name=user.name,
        company_name=company.name,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    normalized_email = payload.email.lower().strip()
    _enforce_login_rate_limit(
        request,
        normalized_email,
    )

    user = (
        db.query(User)
        .filter(
            User.email
            == normalized_email
        )
        .first()
    )

    if (
        not user
        or not verify_password(
            payload.password,
            user.password_hash,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
        )

    if not user.active:
        raise HTTPException(
            status_code=403,
            detail="Usuário inativo",
        )

    _clear_login_rate_limit(
        request,
        normalized_email,
    )

    return TokenResponse(
        access_token=create_access_token(
            str(user.id),
            user.company_id,
            user.session_version,
        ),
        user_name=user.name,
        company_name=user.company.name,
    )


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.session_version += 1
    db.commit()

    return {
        "status": "ok",
        "message": "Sessão encerrada com segurança",
    }


@router.get("/me", response_model=MeResponse)
def me(
    current_user: User = Depends(get_current_user),
):

    return MeResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=(
            "platform_admin"
            if is_platform_admin(current_user)
            else current_user.role
        ),
        company_id=current_user.company_id,
        company_name=current_user.company.name,
    )



@router.post(
    "/recovery/reset-password",
    include_in_schema=False,
)
def recovery_reset_password(
    payload: dict,
    x_recovery_key: str = Header(
        ...,
        alias="X-Recovery-Key",
    ),
    db: Session = Depends(get_db),
):
    expected_key = _recovery_key()

    if not hmac.compare_digest(
        x_recovery_key,
        expected_key,
    ):
        raise HTTPException(
            status_code=403,
            detail="Acesso negado",
        )

    email = str(
        payload.get("email", "")
    ).lower().strip()

    new_password = str(
        payload.get("new_password", "")
    )

    if not email:
        raise HTTPException(
            status_code=422,
            detail="E-mail obrigatorio",
        )

    if len(new_password) < 8:
        raise HTTPException(
            status_code=422,
            detail="A nova senha deve possuir pelo menos 8 caracteres",
        )

    if len(new_password) > 128:
        raise HTTPException(
            status_code=422,
            detail="A nova senha excede o tamanho permitido",
        )

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuario nao encontrado",
        )

    user.password_hash = hash_password(
        new_password
    )
    user.session_version += 1

    db.commit()

    return {
        "status": "ok",
        "message": "Senha redefinida com sucesso",
        "user_id": user.id,
        "email": user.email,
    }

@router.get(
    "/recovery/users",
    include_in_schema=False,
)
def recovery_users(
    x_recovery_key: str = Header(
        ...,
        alias="X-Recovery-Key",
    ),
    db: Session = Depends(get_db),
):

    allow_user_listing = os.getenv(
        "PRINTFLOW_ALLOW_RECOVERY_USER_LIST",
        "false",
    ).strip().lower() in {"1", "true", "yes"}

    if not allow_user_listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso indisponivel",
        )

    expected_key = _recovery_key()

    if not hmac.compare_digest(
        x_recovery_key,
        expected_key,
    ):
        raise HTTPException(
            status_code=403,
            detail="Acesso negado",
        )

    users = (
        db.query(User)
        .order_by(User.id.asc())
        .all()
    )

    return {
        "users": [
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "active": user.active,
                "company_id": user.company_id,
                "company_name": (
                    user.company.name
                    if user.company
                    else None
                ),
            }
            for user in users
        ]
    }

