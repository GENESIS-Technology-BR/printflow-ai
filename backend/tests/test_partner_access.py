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


def test_partner_company_printer_scope(tenant_db):
    from backend.modules.partners.router import partner_company_printers
    from backend.modules.printers.model import Printer
    db = tenant_db
    first = Partner(name="Parceiro A")
    second = Partner(name="Parceiro B")
    db.add_all([first, second])
    db.flush()
    a = Company(name="Cliente A", partner_id=first.id)
    b = Company(name="Cliente B", partner_id=second.id)
    db.add_all([a, b])
    db.flush()
    user = User(company_id=a.id, name="Gestor A", email="fleet@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=first.id, user_id=user.id, role="partner_viewer"))
    db.flush()
    assert partner_company_printers(a.id, user=user, db=db) == []
    with pytest.raises(HTTPException) as exc:
        partner_company_printers(b.id, user=user, db=db)
    assert exc.value.status_code == 403


def test_partner_company_alert_scope(tenant_db):
    from backend.modules.partners.router import partner_company_alerts
    db = tenant_db
    first = Partner(name="Parceiro A")
    second = Partner(name="Parceiro B")
    db.add_all([first, second])
    db.flush()
    a = Company(name="Empresa A", partner_id=first.id)
    b = Company(name="Empresa B", partner_id=second.id)
    db.add_all([a, b])
    db.flush()
    user = User(company_id=a.id, name="Operador", email="alerts-scope@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=first.id, user_id=user.id, role="partner_viewer"))
    db.flush()
    assert partner_company_alerts(a.id, user=user, db=db) == []
    with pytest.raises(HTTPException) as exc:
        partner_company_alerts(b.id, user=user, db=db)
    assert exc.value.status_code == 403


def test_empty_partner_portfolio_summary(tenant_db):
    from backend.modules.partners.router import partner_portfolio_summary
    db = tenant_db
    partner = Partner(name="Parceiro sem clientes")
    db.add(partner)
    db.flush()
    company = Company(name="Empresa legado")
    db.add(company)
    db.flush()
    user = User(company_id=company.id, name="Gestor", email="empty-portfolio@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=partner.id, user_id=user.id, role="partner_admin"))
    db.flush()
    assert partner_portfolio_summary(user=user, db=db) == {
        "companies": 0, "active_printers": 0, "online_printers": 0, "offline_printers": 0
    }


def test_partner_directory_platform_only(tenant_db):
    from backend.modules.partners.router import partner_directory
    db = tenant_db
    partner = Partner(name="SupriTech")
    db.add(partner)
    db.flush()
    company = Company(name="Empresa de teste")
    db.add(company)
    db.flush()
    user = User(company_id=company.id, name="Leitor", email="directory@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    with pytest.raises(HTTPException) as exc:
        partner_directory(user=user, db=db)
    assert exc.value.status_code == 403
    user.role = "platform_admin"
    assert partner_directory(user=user, db=db) == [{"id": partner.id, "name": "SupriTech", "active": True}]


def test_portal_toggle_requires_partner_admin(tenant_db):
    from backend.modules.partners.router import set_customer_portal, CustomerPortalSettings
    db = tenant_db
    partner = Partner(name="Parceiro portal")
    db.add(partner)
    db.flush()
    company = Company(name="Cliente portal", partner_id=partner.id)
    db.add(company)
    db.flush()
    user = User(company_id=company.id, name="Operador", email="portal-role@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    membership = PartnerMembership(partner_id=partner.id, user_id=user.id, role="partner_operator")
    db.add(membership)
    db.flush()
    with pytest.raises(HTTPException) as exc:
        set_customer_portal(company.id, CustomerPortalSettings(enabled=True), user=user, db=db)
    assert exc.value.status_code == 403
    assert company.customer_portal_enabled is False
    membership.role = "partner_admin"
    result = set_customer_portal(company.id, CustomerPortalSettings(enabled=True), user=user, db=db)
    assert result["customer_portal_enabled"] is True
    assert company.customer_portal_enabled is True


def test_unassigned_company_portal_cannot_be_enabled(tenant_db):
    from backend.modules.partners.router import set_customer_portal, CustomerPortalSettings
    db = tenant_db
    company = Company(name="Cliente legado")
    db.add(company)
    db.flush()
    admin = User(company_id=company.id, name="Plataforma", email="unassigned-portal@example.test", password_hash="test", role="platform_admin")
    db.add(admin)
    db.flush()
    with pytest.raises(HTTPException) as exc:
        set_customer_portal(company.id, CustomerPortalSettings(enabled=True), user=admin, db=db)
    assert exc.value.status_code == 409
    assert company.customer_portal_enabled is False


def test_partner_portfolio_does_not_count_other_partner_printers(tenant_db):
    from backend.modules.partners.router import partner_portfolio_summary
    from backend.modules.printers.model import Printer
    db = tenant_db
    first = Partner(name="Carteira A")
    second = Partner(name="Carteira B")
    db.add_all([first, second])
    db.flush()
    a = Company(name="Cliente carteira A", partner_id=first.id)
    b = Company(name="Cliente carteira B", partner_id=second.id)
    db.add_all([a, b])
    db.flush()
    user = User(company_id=a.id, name="Gestor", email="portfolio-scope@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=first.id, user_id=user.id, role="partner_admin"))
    db.flush()
    result = partner_portfolio_summary(user=user, db=db)
    assert result == {"companies": 1, "active_printers": 0, "online_printers": 0, "offline_printers": 0}


def test_create_partner_platform_only_and_no_company_reassignment(tenant_db):
    from backend.modules.partners.router import create_partner, PartnerCreateRequest
    db = tenant_db
    company = Company(name="Guerra homologação")
    db.add(company)
    db.flush()
    user = User(company_id=company.id, name="Gestor", email="create-partner@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    with pytest.raises(HTTPException) as exc:
        create_partner(PartnerCreateRequest(name="SupriTech"), user=user, db=db)
    assert exc.value.status_code == 403
    user.role = "platform_admin"
    result = create_partner(PartnerCreateRequest(name="SupriTech"), user=user, db=db)
    assert result["name"] == "SupriTech"
    assert db.get(Company, company.id).partner_id is None
    with pytest.raises(HTTPException) as exc:
        create_partner(PartnerCreateRequest(name="SupriTech"), user=user, db=db)
    assert exc.value.status_code == 409


def test_portfolio_and_company_overview_use_same_printer_exclusions(tenant_db):
    from backend.modules.partners.router import partner_portfolio_summary, partner_company_overview
    from backend.modules.printers.model import Printer
    db = tenant_db
    partner = Partner(name="Parceiro KPI")
    db.add(partner)
    db.flush()
    company = Company(name="Cliente KPI", partner_id=partner.id)
    db.add(company)
    db.flush()
    user = User(company_id=company.id, name="Gestor", email="kpi-consistency@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=partner.id, user_id=user.id, role="partner_admin"))
    db.add_all([
        Printer(company_id=company.id, ip="10.20.1.1", name="Impressora escritório", model="LaserJet", status="online", active=True),
        Printer(company_id=company.id, ip="10.20.1.2", name="Etiquetas", model="Zebra ZT230", status="offline", active=True),
    ])
    db.flush()
    portfolio = partner_portfolio_summary(user=user, db=db)
    overview = partner_company_overview(company.id, user=user, db=db)
    assert portfolio["active_printers"] == overview["total_active_printers"]
    assert portfolio["online_printers"] == overview["online_printers"]
    assert portfolio["offline_printers"] == overview["offline_printers"]


def test_partner_printer_inventory_exposes_only_operational_allowlist(tenant_db):
    from backend.modules.partners.router import partner_company_printers
    from backend.modules.printers.model import Printer
    db = tenant_db
    partner = Partner(name="Parceiro inventário")
    db.add(partner)
    db.flush()
    company = Company(name="Cliente inventário", partner_id=partner.id)
    db.add(company)
    db.flush()
    user = User(company_id=company.id, name="Gestor", email="inventory-safe@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=partner.id, user_id=user.id, role="partner_viewer"))
    db.add(Printer(company_id=company.id, ip="10.30.1.4", name="Laser", status="online", active=True))
    db.flush()
    rows = partner_company_printers(company.id, user=user, db=db)
    assert len(rows) == 1
    assert set(rows[0]) == {"id", "ip", "name", "unit_name", "sector_name", "manufacturer", "model", "status", "active", "page_count", "toner_percent", "last_seen"}
    assert "agent_token" not in str(rows)


def test_partner_inventory_denies_unrelated_tenant_even_with_known_company_id(tenant_db):
    from backend.modules.partners.router import partner_company_printers
    db = tenant_db
    own_partner = Partner(name="Parceiro autorizado")
    other_partner = Partner(name="Parceiro externo")
    db.add_all([own_partner, other_partner])
    db.flush()
    own = Company(name="Empresa autorizada", partner_id=own_partner.id)
    other = Company(name="Empresa externa", partner_id=other_partner.id)
    db.add_all([own, other])
    db.flush()
    user = User(company_id=own.id, name="Leitor", email="tenant-inventory@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=own_partner.id, user_id=user.id, role="partner_viewer"))
    db.flush()
    with pytest.raises(HTTPException) as exc:
        partner_company_printers(other.id, user=user, db=db)
    assert exc.value.status_code == 403


def test_partner_alerts_denies_unrelated_tenant_even_with_known_company_id(tenant_db):
    from backend.modules.partners.router import partner_company_alerts
    db = tenant_db
    own_partner = Partner(name="Parceiro alerta autorizado")
    other_partner = Partner(name="Parceiro alerta externo")
    db.add_all([own_partner, other_partner])
    db.flush()
    own = Company(name="Empresa alertas autorizada", partner_id=own_partner.id)
    other = Company(name="Empresa alertas externa", partner_id=other_partner.id)
    db.add_all([own, other])
    db.flush()
    user = User(company_id=own.id, name="Leitor", email="tenant-alerts@example.test", password_hash="test", role="client")
    db.add(user)
    db.flush()
    db.add(PartnerMembership(partner_id=own_partner.id, user_id=user.id, role="partner_viewer"))
    db.flush()
    with pytest.raises(HTTPException) as exc:
        partner_company_alerts(other.id, user=user, db=db)
    assert exc.value.status_code == 403
