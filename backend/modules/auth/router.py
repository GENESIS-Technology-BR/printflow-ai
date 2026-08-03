from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
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


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")

    company = Company(name=payload.company_name.strip())
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
        access_token=create_access_token(str(user.id), company.id),
        user_name=user.name,
        company_name=company.name,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
        )
    if not user.active:
        raise HTTPException(status_code=403, detail="Usuário inativo")

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.company_id),
        user_name=user.name,
        company_name=user.company.name,
    )


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return MeResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        company_id=current_user.company_id,
        company_name=current_user.company.name,
    )
