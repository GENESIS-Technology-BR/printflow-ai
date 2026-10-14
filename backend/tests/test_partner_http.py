"""HTTP-level authorization regression tests for TALVOA partner routes.

Uses an in-memory database and overrides auth/DB dependencies. Never touches
production data, external services, or the real Agent.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database.connection import Base
from backend.app.database import models as registered_models  # noqa: F401
from backend.main import app
from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.partners.model import Partner, PartnerMembership


@pytest.fixture()
def http_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    company = Company(name="Tenant A")
    outsider = Company(name="Tenant B")
    partner = Partner(name="Parceiro A")
    other_partner = Partner(name="Parceiro B")
    db.add_all([company, outsider, partner, other_partner])
    db.flush()
    company.partner_id = partner.id
    outsider.partner_id = other_partner.id
    admin = User(company_id=company.id, name="Plataforma", email="platform-http@example.test", password_hash="test", role="platform_admin")
    member = User(company_id=company.id, name="Parceiro", email="member-http@example.test", password_hash="test", role="client")
    db.add_all([admin, member])
    db.flush()
    db.add(PartnerMembership(partner_id=partner.id, user_id=member.id, role="partner_viewer"))
    db.flush()
    identity = {"user": member}
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: identity["user"]
    try:
        client = TestClient(app, base_url="http://localhost")
        yield client, db, identity, admin, member, company, outsider, partner
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        db.close()
        engine.dispose()


def test_http_partner_cannot_read_other_company(http_context):
    client, _, _, _, _, own, outsider, _ = http_context
    assert client.get(f"/api/v1/partners/companies/{own.id}/overview").status_code == 200
    assert client.get(f"/api/v1/partners/companies/{outsider.id}/overview").status_code == 403
    assert client.get(f"/api/v1/partners/companies/{outsider.id}/printers").status_code == 403
    assert client.get(f"/api/v1/partners/companies/{outsider.id}/alerts").status_code == 403


def test_http_onboarding_requires_platform_role(http_context):
    client, _, identity, admin, _, _, _, partner = http_context
    assert client.post("/api/v1/partners/directory", json={"name": "Novo parceiro"}).status_code == 403
    assert client.post(f"/api/v1/partners/directory/{partner.id}/members", json={"user_id": 2, "role": "partner_admin"}).status_code == 403
    identity["user"] = admin
    response = client.post("/api/v1/partners/directory", json={"name": "Novo parceiro"})
    assert response.status_code == 201, response.text
    assert client.post("/api/v1/partners/directory", json={"name": "Novo parceiro"}).status_code == 409


def test_http_portal_opt_in_requires_partner_admin(http_context):
    client, db, identity, admin, member, company, _, partner = http_context
    path = f"/api/v1/partners/companies/{company.id}/customer-portal"
    assert client.patch(path, json={"enabled": True}).status_code == 403
    identity["user"] = admin
    response = client.patch(path, json={"enabled": True})
    assert response.status_code == 200, response.text
    assert response.json()["customer_portal_enabled"] is True
    assert db.get(Company, company.id).customer_portal_enabled is True


def test_http_partner_viewer_cannot_toggle_portal_even_for_own_company(http_context):
    client, _, _, _, _, company, _, _ = http_context
    response = client.patch(f"/api/v1/partners/companies/{company.id}/customer-portal", json={"enabled": True})
    assert response.status_code == 403


def test_http_partner_viewer_cannot_assign_existing_company(http_context):
    client, _, _, _, _, company, _, partner = http_context
    response = client.post(f"/api/v1/partners/directory/{partner.id}/companies/{company.id}")
    assert response.status_code == 403


def test_http_platform_cannot_transfer_company_between_partners(http_context):
    client, db, identity, admin, _, company, outsider, partner = http_context
    identity["user"] = admin
    response = client.post(f"/api/v1/partners/directory/{partner.id}/companies/{outsider.id}")
    assert response.status_code == 409
    assert db.get(Company, outsider.id).partner_id != partner.id


def test_http_customer_portal_is_disabled_by_default(http_context):
    client, db, identity, admin, _, company, _, _ = http_context
    assert db.get(Company, company.id).customer_portal_enabled is False
    identity["user"] = admin
    response = client.get("/api/v1/partners/my-companies")
    assert response.status_code == 200
    selected = next(item for item in response.json() if item["id"] == company.id)
    assert selected["customer_portal_enabled"] is False


@pytest.fixture()
def real_auth_http_context(http_context):
    """Exercise actual JWT/cookie/CSRF dependency, not an authentication mock."""
    from backend.modules.auth.security import create_access_token
    client, db, _, _, member, company, outsider, partner = http_context
    app.dependency_overrides.pop(get_current_user, None)
    token = create_access_token(str(member.id), company.id, member.session_version)
    return client, token, company, outsider


def test_http_real_auth_rejects_missing_session(real_auth_http_context):
    client, _, company, _ = real_auth_http_context
    assert client.get(f"/api/v1/partners/companies/{company.id}/overview").status_code == 401


def test_http_real_auth_cookie_requires_csrf_for_mutation(real_auth_http_context):
    from backend.modules.auth.dependencies import AUTH_COOKIE_NAME
    client, token, company, _ = real_auth_http_context
    client.cookies.set(AUTH_COOKIE_NAME, token)
    assert client.get(f"/api/v1/partners/companies/{company.id}/overview").status_code == 200
    path = f"/api/v1/partners/companies/{company.id}/customer-portal"
    response = client.patch(path, json={"enabled": True})
    assert response.status_code == 403
    assert response.json()["detail"] == "Proteção CSRF inválida"
    response = client.patch(path, json={"enabled": True}, headers={"X-CSRF-Protection": "1"})
    assert response.status_code == 403  # CSRF valid, but viewer cannot mutate
    assert response.json()["detail"] != "Proteção CSRF inválida"


def test_http_real_auth_enforces_cross_partner_scope(real_auth_http_context):
    client, token, _, outsider = real_auth_http_context
    response = client.get(f"/api/v1/partners/companies/{outsider.id}/overview", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_http_real_auth_rejects_invalid_and_expired_tokens(real_auth_http_context):
    from backend.modules.auth.security import create_access_token
    import jwt
    import os
    from datetime import datetime, timedelta, timezone
    client, _, company, _ = real_auth_http_context
    path = f"/api/v1/partners/companies/{company.id}/overview"
    assert client.get(path, headers={"Authorization": "Bearer invalid.jwt.token"}).status_code == 401
    now = datetime.now(timezone.utc)
    expired = jwt.encode({
        "sub": "1", "company_id": company.id, "session_version": 0,
        "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1), "jti": "expired-test",
    }, os.environ["JWT_SECRET"], algorithm="HS256")
    assert client.get(path, headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_http_real_auth_rejects_revoked_session(real_auth_http_context):
    client, token, company, _ = real_auth_http_context
    from backend.modules.auth.model import User
    db_override = app.dependency_overrides[get_db]
    db = db_override()
    user = db.query(User).filter(User.company_id == company.id, User.role == "client").first()
    user.session_version = (user.session_version or 0) + 1
    db.flush()
    response = client.get(f"/api/v1/partners/companies/{company.id}/overview", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_http_inventory_excludes_inactive_printers(http_context):
    from backend.modules.printers.model import Printer
    client, db, _, _, _, company, _, _ = http_context
    db.add_all([
        Printer(company_id=company.id, ip="10.99.0.10", name="Ativa", active=True, status="online"),
        Printer(company_id=company.id, ip="10.99.0.11", name="Desativada", active=False, status="offline"),
    ])
    db.flush()
    response = client.get(f"/api/v1/partners/companies/{company.id}/printers")
    assert response.status_code == 200, response.text
    ips = [item["ip"] for item in response.json()]
    assert "10.99.0.10" in ips
    assert "10.99.0.11" not in ips


def test_http_platform_partner_preview_is_scoped_and_read_only(http_context):
    client, db, identity, admin, _, own, outsider, partner = http_context
    path = f"/api/v1/partners/directory/{partner.id}/preview-companies"
    assert client.get(path).status_code == 403
    identity["user"] = admin
    response = client.get(path)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["preview_only"] is True
    assert data["partner"]["name"] == "Parceiro A"
    assert [item["id"] for item in data["companies"]] == [own.id]
    assert outsider.id not in [item["id"] for item in data["companies"]]
    assert db.get(Company, own.id).customer_portal_enabled is False
    assert client.get("/api/v1/partners/directory/999999/preview-companies").status_code == 404


def test_homologation_origin_preflight_allowed(http_context):
    client, *_ = http_context
    response = client.options(
        "/api/v1/partners/me",
        headers={
            "Origin": "https://talvoa-supritech-homolog.onrender.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers["access-control-allow-origin"] == "https://talvoa-supritech-homolog.onrender.com"
    assert response.headers["access-control-allow-credentials"] == "true"
