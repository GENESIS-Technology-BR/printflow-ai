"""Authorization regression tests for partner-scoped access.

Run after the partner schema has been registered in the application's metadata.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.database.connection import Base
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.partners.model import Partner, PartnerMembership
from backend.modules.partners.access import require_partner_company_access


@pytest.fixture()
def tenant_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_partner_cannot_access_other_partner(tenant_db):
    db = tenant_db
    first = Partner(name="SupriTech")
    second = Partner(name="Outro parceiro")
    db.add_all([first, second])
    db.flush()
    guerra = Company(name="Guerra Implementos", partner_id=first.id)
    outsider = Company(name="Cliente externo", partner_id=second.id)
    db.add_all([guerra, outsider])
    db.flush()
    user = User(company_id=guerra.id, name="Operador", email="operator@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=first.id, user_id=user.id, role="partner_operator"))
    db.flush()
    assert require_partner_company_access(db, user, guerra.id, write=True).id == guerra.id
    with pytest.raises(HTTPException) as exc:
        require_partner_company_access(db, user, outsider.id)
    assert exc.value.status_code == 403


def test_customer_portal_is_opt_in(tenant_db):
    db = tenant_db
    company = Company(name="Guerra Implementos", customer_portal_enabled=False)
    db.add(company)
    db.flush()
    user = User(company_id=company.id, name="Cliente", email="client@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    with pytest.raises(HTTPException) as exc:
        require_partner_company_access(db, user, company.id)
    assert exc.value.status_code == 403
    company.customer_portal_enabled = True
    assert require_partner_company_access(db, user, company.id).id == company.id
    with pytest.raises(HTTPException) as exc:
        require_partner_company_access(db, user, company.id, write=True)
    assert exc.value.status_code == 403
