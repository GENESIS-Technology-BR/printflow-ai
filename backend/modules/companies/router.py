import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_company_admin, get_current_user
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.companies.schema import CompanyResponse, CompanyUpdate
from backend.modules.control_center.router import _agent_communication

router = APIRouter(prefix="/companies", tags=["Companies"])


def _current_user_company(current_user: User, db: Session) -> Company:
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return company


@router.get("/current", response_model=CompanyResponse)
def current_company(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _current_user_company(current_user, db)


@router.get("/current/agent-status")
def current_agent_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = _current_user_company(current_user, db)
    online, stale, communication = _agent_communication(company)
    return {
        "online": online,
        "stale": stale,
        "communication_state": communication,
        "status": company.agent_status,
        "name": company.agent_name,
        "version": company.agent_version,
        "last_seen": company.agent_last_seen,
        "last_error": company.agent_last_error,
    }


@router.patch("/current", response_model=CompanyResponse)
def update_current_company(
    payload: CompanyUpdate,
    current_user: User = Depends(get_company_admin),
    db: Session = Depends(get_db),
):
    company = _current_user_company(current_user, db)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)
    return company


@router.post("/current/regenerate-agent-token", response_model=CompanyResponse)
def regenerate_agent_token(
    current_user: User = Depends(get_company_admin),
    db: Session = Depends(get_db),
):
    company = _current_user_company(current_user, db)
    company.agent_token = secrets.token_urlsafe(32)
    db.commit()
    db.refresh(company)
    return company
