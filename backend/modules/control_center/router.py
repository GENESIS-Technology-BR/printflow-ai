import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.alerts.model import OperationalAlert
from backend.modules.auth.dependencies import get_platform_admin
from backend.modules.auth.model import User
from backend.modules.auth.security import hash_password
from backend.modules.companies.model import Company
from backend.modules.printers.model import Printer

from .schema import (
    ControlCenterClientCreate,
    ControlCenterClientCreated,
    ControlCenterCompany,
    ControlCenterOverview,
)


router = APIRouter(
    prefix="/control-center",
    tags=["Control Center"],
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _agent_online(company: Company) -> bool:
    if not company.active or not company.agent_last_seen:
        return False

    elapsed = (
        datetime.now(timezone.utc)
        - _utc(company.agent_last_seen)
    )

    return elapsed <= timedelta(minutes=30)



@router.post(
    "/clients",
    response_model=ControlCenterClientCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_control_center_client(
    payload: ControlCenterClientCreate,
    current_user: User = Depends(
        get_platform_admin
    ),
    db: Session = Depends(get_db),
):
    email = str(
        payload.email
    ).lower().strip()

    company_name = (
        payload.company_name.strip()
    )

    responsible_name = (
        payload.responsible_name.strip()
    )

    if len(company_name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Nome da empresa inválido",
        )

    if len(responsible_name) < 3:
        raise HTTPException(
            status_code=422,
            detail="Nome do responsável inválido",
        )

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="E-mail já cadastrado",
        )

    temporary_password = (
        secrets.token_urlsafe(12)
    )

    company = Company(
        name=company_name,
        plan="pilot",
    )

    try:
        db.add(company)
        db.flush()

        user = User(
            company_id=company.id,
            name=responsible_name,
            email=email,
            password_hash=hash_password(
                temporary_password
            ),
            role="admin",
            active=True,
        )

        db.add(user)
        db.commit()

        db.refresh(company)
        db.refresh(user)

    except Exception:
        db.rollback()
        raise

    return ControlCenterClientCreated(
        company_id=company.id,
        company_uuid=company.uuid,
        company_name=company.name,
        plan=company.plan,
        user_id=user.id,
        responsible_name=user.name,
        email=user.email,
        temporary_password=(
            temporary_password
        ),
        agent_token=company.agent_token,
    )


@router.get(
    "/overview",
    response_model=ControlCenterOverview,
)
def overview(
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    companies = (
        db.query(Company)
        .order_by(Company.name.asc())
        .all()
    )

    items: list[ControlCenterCompany] = []

    total_active_printers = 0
    total_open_alerts = 0
    total_agents_online = 0

    for company in companies:
        active_query = (
            db.query(Printer)
            .filter(
                Printer.company_id == company.id,
                Printer.active.is_(True),
            )
        )

        active_printers = active_query.count()

        online_printers = (
            active_query
            .filter(Printer.status == "online")
            .count()
        )

        offline_printers = (
            active_query
            .filter(Printer.status == "offline")
            .count()
        )

        alerts = (
            db.query(OperationalAlert)
            .filter(
                OperationalAlert.company_id
                == company.id,
                OperationalAlert.status.in_(
                    ("open", "acknowledged")
                ),
            )
            .count()
        )

        agent_online = _agent_online(company)

        total_active_printers += active_printers
        total_open_alerts += alerts

        if agent_online:
            total_agents_online += 1

        items.append(
            ControlCenterCompany(
                id=company.id,
                uuid=company.uuid,
                name=company.name,
                plan=company.plan,
                active=company.active,
                agent_online=agent_online,
                agent_status=company.agent_status,
                agent_version=company.agent_version,
                agent_last_seen=company.agent_last_seen,
                active_printers=active_printers,
                online_printers=online_printers,
                offline_printers=offline_printers,
                alerts=alerts,
            )
        )

    return ControlCenterOverview(
        generated_at=datetime.now(timezone.utc),
        companies_total=len(companies),
        companies_active=sum(
            1 for company in companies
            if company.active
        ),
        agents_online=total_agents_online,
        active_printers=total_active_printers,
        open_alerts=total_open_alerts,
        companies=items,
    )
