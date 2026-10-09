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
    from sqlalchemy import func
    from backend.modules.printers.model import Printer

    if user.role == "platform_admin":
        companies = db.query(Company.id).filter(Company.active.is_(True)).all()
    else:
        companies = (
            db.query(Company.id)
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
    company_ids = [item[0] for item in companies]
    if not company_ids:
        return {"companies": 0, "active_printers": 0, "online_printers": 0, "offline_printers": 0}
    status_rows = (
        db.query(Printer.status, func.count(Printer.id))
        .filter(Printer.company_id.in_(company_ids), Printer.active.is_(True))
        .group_by(Printer.status)
        .all()
    )
    counts = {str(status or "").lower(): count for status, count in status_rows}
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
    from backend.modules.dashboard.router import serialize_printer
    from backend.modules.usage.router import _exclude_label_printers_for_company
    company = require_partner_company_access(db, user, company_id)
    printers = db.query(Printer).filter(Printer.company_id == company.id).order_by(Printer.id.desc()).all()
    printers = _exclude_label_printers_for_company(company, printers)
    return [serialize_printer(printer) for printer in printers]


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
