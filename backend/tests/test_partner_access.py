"""Authorization regression tests for partner-scoped access.

Run after the partner schema has been registered in the application's metadata.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.database.connection import Base
from backend.app.database import models as registered_models  # noqa: F401
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


def test_inactive_partner_denied(tenant_db):
    db = tenant_db
    partner = Partner(name="Parceiro suspenso", active=False)
    db.add(partner)
    db.flush()
    company = Company(name="Empresa", partner_id=partner.id)
    db.add(company)
    db.flush()
    user = User(company_id=company.id, name="Gestor", email="suspended@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=partner.id, user_id=user.id, role="partner_admin"))
    db.flush()
    with pytest.raises(HTTPException) as exc:
        require_partner_company_access(db, user, company.id)
    assert exc.value.status_code == 403


def test_partner_viewer_cannot_write(tenant_db):
    db = tenant_db
    partner = Partner(name="Parceiro leitura")
    db.add(partner)
    db.flush()
    company = Company(name="Empresa leitura", partner_id=partner.id)
    db.add(company)
    db.flush()
    user = User(company_id=company.id, name="Leitor", email="viewer@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=partner.id, user_id=user.id, role="partner_viewer"))
    db.flush()
    assert require_partner_company_access(db, user, company.id).id == company.id
    with pytest.raises(HTTPException) as exc:
        require_partner_company_access(db, user, company.id, write=True)
    assert exc.value.status_code == 403


def test_platform_admin_can_view_unassigned_company(tenant_db):
    db = tenant_db
    company = Company(name="Homologação sem parceiro")
    db.add(company)
    db.flush()
    admin = User(company_id=company.id, name="TALVOA", email="platform@example.test", password_hash="test", role="platform_admin")
    db.add(admin)
    db.flush()
    assert require_partner_company_access(db, admin, company.id, write=True).id == company.id


def test_inactive_membership_denied(tenant_db):
    db = tenant_db
    partner = Partner(name="SupriTech")
    db.add(partner)
    db.flush()
    company = Company(name="Guerra Implementos", partner_id=partner.id)
    db.add(company)
    db.flush()
    user = User(company_id=company.id, name="Operador", email="inactive@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=partner.id, user_id=user.id, role="partner_admin", active=False))
    db.flush()
    with pytest.raises(HTTPException) as exc:
        require_partner_company_access(db, user, company.id)
    assert exc.value.status_code == 403


def test_customer_portal_guard_on_partner_assignment(tenant_db):
    from backend.modules.partners.access import require_legacy_company_portal_access
    db = tenant_db
    company = Company(name="Cliente legado")
    db.add(company)
    db.flush()
    user = User(company_id=company.id, name="Cliente", email="guard@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    assert require_legacy_company_portal_access(db, user).id == company.id
    partner = Partner(name="Parceiro")
    db.add(partner)
    db.flush()
    company.partner_id = partner.id
    with pytest.raises(HTTPException) as exc:
        require_legacy_company_portal_access(db, user)
    assert exc.value.status_code == 403
    company.customer_portal_enabled = True
    assert require_legacy_company_portal_access(db, user).id == company.id
