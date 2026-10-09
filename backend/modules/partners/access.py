"""Partner/customer authorization primitives.

All access checks are fail-closed. No database schema changes are performed
by importing this module. Platform admins are explicitly privileged; partner
membership alone never grants access to unrelated companies.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from .model import PartnerMembership

PARTNER_ROLES = frozenset({"partner_admin", "partner_operator", "partner_viewer"})
PARTNER_WRITE_ROLES = frozenset({"partner_admin", "partner_operator"})


def require_partner_company_access(
    db: Session,
    user: User,
    company_id: int,
    *,
    write: bool = False,
) -> Company:
    """Authorize access to a company owned by the authenticated partner.

    Never authorize merely because the caller supplies a company_id.
    A user with a legacy company-level account can access their own company
    only when its final-customer portal is enabled.
    """
    company = db.query(Company).filter(Company.id == company_id, Company.active.is_(True)).first()
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")

    if user.role == "platform_admin":
        return company

    if company.partner_id is not None:
        memberships = (
            db.query(PartnerMembership)
            .filter(
                PartnerMembership.user_id == user.id,
                PartnerMembership.partner_id == company.partner_id,
                PartnerMembership.active.is_(True),
            )
            .all()
        )
        allowed = PARTNER_WRITE_ROLES if write else PARTNER_ROLES
        if any(m.role in allowed for m in memberships):
            return company

    if (
        not write
        and company.customer_portal_enabled
        and user.company_id == company.id
        and user.role in {"client", "admin"}
    ):
        return company

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso não autorizado à empresa")
