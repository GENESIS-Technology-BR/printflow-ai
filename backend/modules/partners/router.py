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
