import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.alerts.model import OperationalAlert
from backend.modules.auth.dependencies import get_platform_admin
from backend.modules.auth.model import User
from backend.modules.auth.security import create_access_token, hash_password
from backend.modules.companies.model import Company
from backend.modules.printers.model import Printer

from .schema import (
    ControlCenterClientCreate,
    ControlCenterClientCreated,
    ControlCenterCompany,
    ControlCenterOverview,
    ControlCenterClientUser,
    ControlCenterClientUserCreate,
    ControlCenterClientUserStatusUpdate,
    ControlCenterPreviewSession,
)


router = APIRouter(
    prefix="/control-center",
    tags=["Control Center"],
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _agent_communication(company: Company) -> tuple[bool, bool, str]:
    if not company.active:
        return False, False, "inactive"

    if not company.agent_last_seen:
        return False, False, "never_seen"

    elapsed = (
        datetime.now(timezone.utc)
        - _utc(company.agent_last_seen)
    )

    if elapsed <= timedelta(minutes=10):
        return True, False, "healthy"

    if elapsed <= timedelta(minutes=30):
        return False, True, "stale"

    return False, False, "offline"


def _onboarding_progress(
    state: str,
) -> tuple[int, str]:
    mapping = {
        "awaiting_agent": (
            25,
            "Instalar o Agent e validar a primeira comunicação.",
        ),
        "agent_connected": (
            60,
            "Aguardar a descoberta das primeiras impressoras.",
        ),
        "pilot_active": (
            100,
            "Piloto operacional: acompanhar estabilidade e relatórios.",
        ),
        "agent_attention": (
            60,
            "Restabelecer a comunicação do Agent antes de avançar.",
        ),
        "inactive": (
            0,
            "Ativar o cliente para iniciar o onboarding.",
        ),
    }
    return mapping.get(
        state,
        (10, "Revisar o cadastro do cliente."),
    )


def _commercial_readiness(
    company: Company,
    onboarding_state: str,
    agent_communication_state: str,
    active_printers: int,
    alerts: int,
) -> tuple[int, bool, list[str]]:
    blockers: list[str] = []
    score = 0

    if company.active:
        score += 20
    else:
        blockers.append("Cliente inativo.")

    if onboarding_state == "pilot_active":
        score += 30
    else:
        blockers.append("Onboarding ainda não concluído.")

    if agent_communication_state == "healthy":
        score += 25
    else:
        blockers.append("Agent sem comunicação saudável.")

    if active_printers > 0:
        score += 15
    else:
        blockers.append("Nenhuma impressora ativa monitorada.")

    if alerts == 0:
        score += 10
    else:
        blockers.append("Existem alertas operacionais pendentes.")

    ready = score == 100
    return score, ready, blockers


def _onboarding_state(
    company: Company,
    active_printers: int,
    agent_communication_state: str,
) -> str:
    if not company.active:
        return "inactive"

    if not company.agent_last_seen:
        return "awaiting_agent"

    if agent_communication_state in ("stale", "offline"):
        return "agent_attention"

    if active_printers <= 0:
        return "agent_connected"

    return "pilot_active"



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
    pilots_ready = 0
    companies_needing_attention = 0
    companies_commercial_ready = 0

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

        (
            agent_online,
            agent_stale,
            agent_communication_state,
        ) = _agent_communication(company)

        total_active_printers += active_printers
        total_open_alerts += alerts

        if agent_online:
            total_agents_online += 1

        onboarding_state = _onboarding_state(
            company,
            active_printers,
            agent_communication_state,
        )

        (
            onboarding_progress,
            onboarding_next_action,
        ) = _onboarding_progress(onboarding_state)

        if onboarding_state == "pilot_active":
            pilots_ready += 1

        if onboarding_state == "agent_attention" or alerts > 0:
            companies_needing_attention += 1

        (
            commercial_readiness_score,
            commercial_ready,
            commercial_blockers,
        ) = _commercial_readiness(
            company,
            onboarding_state,
            agent_communication_state,
            active_printers,
            alerts,
        )

        if commercial_ready:
            companies_commercial_ready += 1

        items.append(
            ControlCenterCompany(
                id=company.id,
                uuid=company.uuid,
                name=company.name,
                plan=company.plan,
                active=company.active,
                agent_online=agent_online,
                agent_stale=agent_stale,
                agent_communication_state=agent_communication_state,
                agent_status=company.agent_status,
                agent_version=company.agent_version,
                agent_last_seen=company.agent_last_seen,
                onboarding_state=onboarding_state,
                onboarding_progress=onboarding_progress,
                onboarding_next_action=onboarding_next_action,
                commercial_readiness_score=commercial_readiness_score,
                commercial_ready=commercial_ready,
                commercial_blockers=commercial_blockers,
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
        pilots_ready=pilots_ready,
        companies_needing_attention=companies_needing_attention,
        companies_commercial_ready=companies_commercial_ready,
        companies=items,
    )


def _find_company_by_uuid(
    db: Session,
    company_uuid: str,
) -> Company:
    company = (
        db.query(Company)
        .filter(Company.uuid == company_uuid)
        .first()
    )
    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada",
        )
    return company


@router.get(
    "/clients/{company_uuid}/users",
    response_model=list[ControlCenterClientUser],
)
def list_client_users(
    company_uuid: str,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    company = _find_company_by_uuid(db, company_uuid)

    return (
        db.query(User)
        .filter(User.company_id == company.id)
        .order_by(User.name.asc(), User.id.asc())
        .all()
    )


@router.post(
    "/clients/{company_uuid}/users",
    response_model=ControlCenterClientUser,
    status_code=status.HTTP_201_CREATED,
)
def create_client_user(
    company_uuid: str,
    payload: ControlCenterClientUserCreate,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    company = _find_company_by_uuid(db, company_uuid)
    email = str(payload.email).lower().strip()

    existing = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="E-mail já cadastrado",
        )

    user = User(
        company_id=company.id,
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="admin",
        active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch(
    "/clients/{company_uuid}/users/{user_id}",
    response_model=ControlCenterClientUser,
)
def update_client_user_status(
    company_uuid: str,
    user_id: int,
    payload: ControlCenterClientUserStatusUpdate,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    company = _find_company_by_uuid(db, company_uuid)
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.company_id == company.id,
        )
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado",
        )

    user.active = payload.active
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/clients/{company_uuid}/preview",
    response_model=ControlCenterPreviewSession,
)
def create_client_preview(
    company_uuid: str,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    company = _find_company_by_uuid(db, company_uuid)

    user = (
        db.query(User)
        .filter(
            User.company_id == company.id,
            User.active.is_(True),
        )
        .order_by(User.id.asc())
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=409,
            detail="O cliente não possui usuário ativo para visualização",
        )

    expires_minutes = 30
    access_token = create_access_token(
        str(user.id),
        company.id,
        expires_minutes=expires_minutes,
    )

    return ControlCenterPreviewSession(
        access_token=access_token,
        expires_minutes=expires_minutes,
        company_id=company.id,
        company_uuid=company.uuid,
        company_name=company.name,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
    )
