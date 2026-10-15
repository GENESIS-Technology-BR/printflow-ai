"""Read-only partner portfolio endpoints.

No token or secret fields are exposed. Company scope is checked server-side.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.partners.model import Partner, PartnerMembership

router = APIRouter(prefix="/partners", tags=["Partners"])


@router.get("/my-companies")
def my_partner_companies(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "platform_admin":
        companies = db.query(Company).filter(Company.active.is_(True)).order_by(Company.name).all()
    else:
        memberships = (
            db.query(PartnerMembership)
            .join(Partner, Partner.id == PartnerMembership.partner_id)
            .filter(
                PartnerMembership.user_id == user.id,
                PartnerMembership.active.is_(True),
                Partner.active.is_(True),
                PartnerMembership.role.in_(("partner_admin", "partner_operator", "partner_viewer")),
            )
            .all()
        )
        ids = [membership.partner_id for membership in memberships]
        if not ids:
            raise HTTPException(status_code=403, detail="Usuário sem vínculo ativo com parceiro")
        companies = (
            db.query(Company)
            .filter(Company.partner_id.in_(ids), Company.active.is_(True))
            .order_by(Company.name)
            .all()
        )
    return [
        {
            "id": company.id,
            "name": company.name,
            "partner_id": company.partner_id,
            "customer_portal_enabled": company.customer_portal_enabled,
            "active": company.active,
        }
        for company in companies
    ]


from pydantic import BaseModel
from backend.modules.partners.access import require_partner_company_access


class CustomerPortalSettings(BaseModel):
    enabled: bool


@router.patch("/companies/{company_id}/customer-portal")
def set_customer_portal(
    company_id: int,
    payload: CustomerPortalSettings,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Only TALVOA or an active partner administrator can grant customer access."""
    company = require_partner_company_access(db, user, company_id, write=True)
    if user.role != "platform_admin":
        is_admin = (
            db.query(PartnerMembership.id)
            .join(Partner, Partner.id == PartnerMembership.partner_id)
            .filter(
                PartnerMembership.user_id == user.id,
                PartnerMembership.partner_id == company.partner_id,
                PartnerMembership.role == "partner_admin",
                PartnerMembership.active.is_(True),
                Partner.active.is_(True),
            )
            .first()
        )
        if not is_admin:
            raise HTTPException(status_code=403, detail="Somente o administrador do parceiro pode configurar o portal")
    if company.partner_id is None and payload.enabled:
        raise HTTPException(status_code=409, detail="Associe a empresa a um parceiro antes de habilitar o portal")
    company.customer_portal_enabled = payload.enabled
    db.commit()
    return {"company_id": company.id, "customer_portal_enabled": company.customer_portal_enabled}


@router.get("/me")
def my_partner_context(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "platform_admin":
        return {"platform_admin": True, "partners": []}
    memberships = (
        db.query(PartnerMembership, Partner)
        .join(Partner, Partner.id == PartnerMembership.partner_id)
        .filter(
            PartnerMembership.user_id == user.id,
            PartnerMembership.active.is_(True),
            Partner.active.is_(True),
            PartnerMembership.role.in_(("partner_admin", "partner_operator", "partner_viewer")),
        )
        .all()
    )
    return {
        "platform_admin": False,
        "partners": [
            {"id": partner.id, "name": partner.name, "role": membership.role}
            for membership, partner in memberships
        ],
    }


@router.get("/companies/{company_id}/overview")
def partner_company_overview(
    company_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Scoped fleet summary. No raw Agent credentials or printer secrets."""
    from backend.modules.printers.model import Printer
    company = require_partner_company_access(db, user, company_id)
    printers = (
        db.query(Printer)
        .filter(Printer.company_id == company.id, Printer.active.is_(True))
        .all()
    )
    from backend.modules.usage.router import _exclude_label_printers_for_company
    printers = _exclude_label_printers_for_company(company, printers)
    online = sum(1 for printer in printers if (printer.status or "").lower() == "online")
    offline = sum(1 for printer in printers if (printer.status or "").lower() == "offline")
    return {
        "company_id": company.id,
        "company_name": company.name,
        "total_active_printers": len(printers),
        "online_printers": online,
        "offline_printers": offline,
        "other_status_printers": len(printers) - online - offline,
        "agent_status": company.agent_status,
        "agent_last_seen": company.agent_last_seen,
    }


@router.get("/portfolio-summary")
def partner_portfolio_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregated company and printer counts, always scoped to partner membership."""
    from backend.modules.printers.model import Printer
    from backend.modules.usage.router import _exclude_label_printers_for_company

    if user.role == "platform_admin":
        companies = db.query(Company).filter(Company.active.is_(True)).all()
    else:
        companies = (
            db.query(Company)
            .join(Partner, Partner.id == Company.partner_id)
            .join(PartnerMembership, PartnerMembership.partner_id == Partner.id)
            .filter(
                PartnerMembership.user_id == user.id,
                PartnerMembership.active.is_(True),
                PartnerMembership.role.in_(("partner_admin", "partner_operator", "partner_viewer")),
                Partner.active.is_(True),
                Company.active.is_(True),
            )
            .distinct()
            .all()
        )
        if not companies:
            membership_exists = (
                db.query(PartnerMembership.id)
                .join(Partner, Partner.id == PartnerMembership.partner_id)
                .filter(
                    PartnerMembership.user_id == user.id,
                    PartnerMembership.active.is_(True),
                    PartnerMembership.role.in_(("partner_admin", "partner_operator", "partner_viewer")),
                    Partner.active.is_(True),
                )
                .first()
            )
            if not membership_exists:
                raise HTTPException(status_code=403, detail="Usuário sem vínculo ativo com parceiro")
    company_ids = [company.id for company in companies]
    if not company_ids:
        return {"companies": 0, "active_printers": 0, "online_printers": 0, "offline_printers": 0}
    printers = db.query(Printer).filter(Printer.company_id.in_(company_ids), Printer.active.is_(True)).all()
    company_by_id = {company.id: company for company in companies}
    grouped = {company_id: [] for company_id in company_ids}
    for printer in printers:
        grouped[printer.company_id].append(printer)
    included = [printer for company_id, group in grouped.items()
                for printer in _exclude_label_printers_for_company(company_by_id[company_id], group)]
    counts = {}
    for printer in included:
        key = str(printer.status or "").lower()
        counts[key] = counts.get(key, 0) + 1
    return {
        "companies": len(company_ids),
        "active_printers": sum(counts.values()),
        "online_printers": counts.get("online", 0),
        "offline_printers": counts.get("offline", 0),
    }


@router.get("/companies/{company_id}/printers")
def partner_company_printers(
    company_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tenant-scoped read-only fleet details for the partner dashboard."""
    from backend.modules.printers.model import Printer
    from backend.modules.usage.router import _exclude_label_printers_for_company
    company = require_partner_company_access(db, user, company_id)
    printers = db.query(Printer).filter(Printer.company_id == company.id, Printer.active.is_(True)).order_by(Printer.id.desc()).all()
    printers = _exclude_label_printers_for_company(company, printers)
    return [
        {
            "id": printer.id,
            "ip": printer.ip,
            "name": printer.custom_name or printer.name,
            "unit_name": printer.unit_name,
            "sector_name": printer.sector_name,
            "manufacturer": printer.manufacturer,
            "model": printer.model,
            "status": printer.status,
            "active": bool(printer.active),
            "page_count": printer.page_count,
            "toner_percent": printer.toner_percent,
            "last_seen": printer.last_seen.isoformat() if printer.last_seen else None,
        }
        for printer in printers
    ]


@router.get("/companies/{company_id}/alerts")
def partner_company_alerts(
    company_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Read-only alert list with explicit tenant authorization."""
    from backend.modules.alerts.model import OperationalAlert
    from backend.modules.alerts.service import serialize_alert
    company = require_partner_company_access(db, user, company_id)
    alerts = (
        db.query(OperationalAlert)
        .filter(OperationalAlert.company_id == company.id)
        .order_by(OperationalAlert.id.desc())
        .limit(100)
        .all()
    )
    return [serialize_alert(alert) for alert in alerts]


@router.get("/directory")
def partner_directory(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Platform-only directory; excludes membership and credential data."""
    if user.role != "platform_admin":
        raise HTTPException(status_code=403, detail="Acesso exclusivo TALVOA")
    partners = db.query(Partner).order_by(Partner.name.asc()).all()
    return [{"id": partner.id, "name": partner.name, "active": partner.active} for partner in partners]


class PartnerCreateRequest(BaseModel):
    name: str


@router.post("/directory", status_code=201)
def create_partner(
    payload: PartnerCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Platform-only onboarding; never reassigns an existing company."""
    if user.role != "platform_admin":
        raise HTTPException(status_code=403, detail="Acesso exclusivo TALVOA")
    name = payload.name.strip()
    if not 2 <= len(name) <= 180:
        raise HTTPException(status_code=422, detail="Nome do parceiro deve ter entre 2 e 180 caracteres")
    from sqlalchemy import func
    existing = db.query(Partner).filter(func.lower(Partner.name) == name.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Parceiro já cadastrado")
    partner = Partner(name=name, active=True)
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return {"id": partner.id, "name": partner.name, "active": partner.active}


class PartnerStatusRequest(BaseModel):
    active: bool


@router.patch("/directory/{partner_id}/status")
def update_partner_status(
    partner_id: int,
    payload: PartnerStatusRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Platform-only partner suspension/reactivation.

    Access to partner-scoped endpoints is denied for suspended partners
    through existing Partner.active checks; no credentials are changed.
    """
    if user.role != "platform_admin":
        raise HTTPException(status_code=403, detail="Acesso exclusivo TALVOA")
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if partner is None:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")
    partner.active = payload.active
    db.commit()
    return {"id": partner.id, "name": partner.name, "active": partner.active}


@router.get("/directory/{partner_id}/members")
def list_partner_members(
    partner_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Platform-only member directory without credentials or password hashes."""
    if user.role != "platform_admin":
        raise HTTPException(status_code=403, detail="Acesso exclusivo TALVOA")
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if partner is None:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")
    memberships = (
        db.query(PartnerMembership, User)
        .join(User, User.id == PartnerMembership.user_id)
        .filter(PartnerMembership.partner_id == partner_id)
        .order_by(User.name.asc(), User.id.asc())
        .all()
    )
    return [{
        "id": membership.id,
        "user_id": member.id,
        "name": member.name,
        "email": member.email,
        "role": membership.role,
        "active": membership.active and member.active,
    } for membership, member in memberships]


class PartnerMemberStatusRequest(BaseModel):
    active: bool


@router.patch("/directory/{partner_id}/members/{membership_id}/status")
def update_partner_member_status(
    partner_id: int,
    membership_id: int,
    payload: PartnerMemberStatusRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Platform-only revocation of one partner membership, not a global user."""
    if user.role != "platform_admin":
        raise HTTPException(status_code=403, detail="Acesso exclusivo TALVOA")
    membership = db.query(PartnerMembership).filter(
        PartnerMembership.id == membership_id,
        PartnerMembership.partner_id == partner_id,
    ).first()
    if membership is None:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")
    if payload.active:
        partner = db.query(Partner).filter(
            Partner.id == partner_id, Partner.active.is_(True)
        ).first()
        member = db.query(User).filter(
            User.id == membership.user_id, User.active.is_(True)
        ).first()
        if partner is None or member is None:
            raise HTTPException(status_code=409, detail="Parceiro ou usuário inativo")
    membership.active = payload.active
    db.commit()
    return {
        "id": membership.id,
        "partner_id": partner_id,
        "user_id": membership.user_id,
        "role": membership.role,
        "active": membership.active,
    }


class PartnerUserCreateRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "partner_admin"


@router.post("/directory/{partner_id}/users", status_code=201)
def create_partner_user(
    partner_id: int,
    payload: PartnerUserCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Platform-only provisioning of a named partner user and membership."""
    from backend.modules.auth.security import hash_password
    from backend.modules.partners.access import PARTNER_ROLES
    from pydantic import EmailStr, TypeAdapter, ValidationError

    if user.role != "platform_admin":
        raise HTTPException(status_code=403, detail="Acesso exclusivo TALVOA")
    partner = db.query(Partner).filter(Partner.id == partner_id, Partner.active.is_(True)).first()
    if partner is None:
        raise HTTPException(status_code=404, detail="Parceiro ativo não encontrado")
    name = payload.name.strip()
    if len(name) < 3 or len(name) > 120:
        raise HTTPException(status_code=422, detail="Nome deve ter entre 3 e 120 caracteres")
    try:
        email = str(TypeAdapter(EmailStr).validate_python(payload.email)).lower().strip()
    except ValidationError:
        raise HTTPException(status_code=422, detail="E-mail inválido")
    if payload.role not in PARTNER_ROLES:
        raise HTTPException(status_code=422, detail="Perfil de parceiro inválido")
    if len(payload.password) < 12 or len(payload.password) > 128:
        raise HTTPException(status_code=422, detail="Senha deve ter entre 12 e 128 caracteres")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")
    # User.company_id is currently required. Use a new, dedicated company
    # for the partner identity, never a customer's tenant.
    company = Company(name=f"Parceiro - {partner.name}", active=True)
    try:
        db.add(company)
        db.flush()
        member = User(
            company_id=company.id,
            name=name,
            email=email,
            password_hash=hash_password(payload.password),
            role="client",
            active=True,
        )
        db.add(member)
        db.flush()
        db.add(PartnerMembership(
            partner_id=partner.id,
            user_id=member.id,
            role=payload.role,
            active=True,
        ))
        db.commit()
        db.refresh(member)
    except Exception:
        db.rollback()
        raise
    return {
        "id": member.id,
        "name": member.name,
        "email": member.email,
        "partner_id": partner.id,
        "role": payload.role,
        "active": member.active,
    }


class PartnerMemberRequest(BaseModel):
    user_id: int
    role: str


@router.post("/directory/{partner_id}/members", status_code=201)
def add_partner_member(
    partner_id: int,
    payload: PartnerMemberRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Platform-only membership provisioning; never changes user credentials."""
    from backend.modules.partners.access import PARTNER_ROLES
    if user.role != "platform_admin":
        raise HTTPException(status_code=403, detail="Acesso exclusivo TALVOA")
    partner = db.query(Partner).filter(Partner.id == partner_id, Partner.active.is_(True)).first()
    if partner is None:
        raise HTTPException(status_code=404, detail="Parceiro ativo não encontrado")
    if payload.role not in PARTNER_ROLES:
        raise HTTPException(status_code=422, detail="Perfil de parceiro inválido")
    member_user = db.query(User).filter(User.id == payload.user_id, User.active.is_(True)).first()
    if member_user is None or member_user.role == "platform_admin":
        raise HTTPException(status_code=404, detail="Usuário elegível não encontrado")
    existing = db.query(PartnerMembership).filter(
        PartnerMembership.partner_id == partner_id,
        PartnerMembership.user_id == payload.user_id,
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Vínculo já cadastrado; atualize-o por fluxo específico")
    membership = PartnerMembership(partner_id=partner_id, user_id=payload.user_id, role=payload.role, active=True)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return {"id": membership.id, "partner_id": partner_id, "user_id": payload.user_id, "role": payload.role, "active": True}


@router.post("/directory/{partner_id}/companies/{company_id}", status_code=200)
def assign_unassigned_company(
    partner_id: int,
    company_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """One-way explicit assignment; never transfer an existing partner's tenant."""
    if user.role != "platform_admin":
        raise HTTPException(status_code=403, detail="Acesso exclusivo TALVOA")
    partner = db.query(Partner).filter(Partner.id == partner_id, Partner.active.is_(True)).first()
    if partner is None:
        raise HTTPException(status_code=404, detail="Parceiro ativo não encontrado")
    company = db.query(Company).filter(Company.id == company_id, Company.active.is_(True)).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa ativa não encontrada")
    if company.partner_id is not None:
        raise HTTPException(status_code=409, detail="Empresa já vinculada; transferência não permitida")
    if company.customer_portal_enabled:
        raise HTTPException(status_code=409, detail="Desative o portal antes de vincular a empresa")
    company.partner_id = partner.id
    db.commit()
    return {"company_id": company.id, "partner_id": partner.id, "customer_portal_enabled": False}


@router.get("/directory/{partner_id}/preview-companies")
def preview_partner_companies(
    partner_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Platform-only read-only view of a partner's exact company scope.

    This is not impersonation: no membership, token or tenant context is changed.
    """
    if user.role != "platform_admin":
        raise HTTPException(status_code=403, detail="Acesso exclusivo TALVOA")
    partner = db.query(Partner).filter(Partner.id == partner_id, Partner.active.is_(True)).first()
    if partner is None:
        raise HTTPException(status_code=404, detail="Parceiro ativo não encontrado")
    companies = db.query(Company).filter(
        Company.partner_id == partner.id, Company.active.is_(True)
    ).order_by(Company.name).all()
    return {
        "partner": {"id": partner.id, "name": partner.name},
        "companies": [{
            "id": company.id,
            "name": company.name,
            "customer_portal_enabled": company.customer_portal_enabled,
        } for company in companies],
        "preview_only": True,
    }
