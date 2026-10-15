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
    assert client.post("/api/v1/partners/directory", json={"name": "  NOVO PARCEIRO  "}).status_code == 409


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


def test_http_integration_scoped_key_isolates_partner_companies(http_context, monkeypatch):
    """Real HTTP requests must not expose another partner's company or aggregates."""
    import json
    client, db, _, _, _, own, outsider, _ = http_context
    key = "integration-test-key-" + "a" * 40
    monkeypatch.setenv("TALVOA_INTEGRATION_SCOPED_KEYS", json.dumps([
        {"company_uuid": own.uuid, "key": key},
    ]))
    headers = {"X-Talvoa-Integration-Key": key}
    allowed = client.get(f"/api/v1/integration/companies/{own.uuid}", headers=headers)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["uuid"] == own.uuid
    denied = client.get(f"/api/v1/integration/companies/{outsider.uuid}", headers=headers)
    assert denied.status_code == 403
    listing = client.get("/api/v1/integration/companies", headers=headers)
    assert listing.status_code == 200, listing.text
    assert [item["uuid"] for item in listing.json()] == [own.uuid]
    status = client.get("/api/v1/integration/status", headers=headers)
    assert status.status_code == 200, status.text
    assert status.json()["companies"] == 1


def test_http_integration_key_denies_inactive_company(http_context, monkeypatch):
    import json
    client, db, _, _, _, own, _, _ = http_context
    key = "integration-test-key-" + "b" * 40
    monkeypatch.setenv("TALVOA_INTEGRATION_SCOPED_KEYS", json.dumps([
        {"company_uuid": own.uuid, "key": key},
    ]))
    own.active = False
    db.flush()
    response = client.get(
        f"/api/v1/integration/companies/{own.uuid}",
        headers={"X-Talvoa-Integration-Key": key},
    )
    assert response.status_code == 403


def test_http_partner_portfolio_summary_excludes_other_partner_and_inactive(http_context):
    from backend.modules.printers.model import Printer
    client, db, _, _, _, own, outsider, _ = http_context
    db.add_all([
        Printer(company_id=own.id, ip="10.99.1.10", name="Own online", active=True, status="online"),
        Printer(company_id=own.id, ip="10.99.1.11", name="Own disabled", active=False, status="offline"),
        Printer(company_id=outsider.id, ip="10.99.2.10", name="Other tenant", active=True, status="offline"),
    ])
    db.flush()
    response = client.get("/api/v1/partners/portfolio-summary")
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["companies"] == 1
    assert summary["active_printers"] == 1
    assert summary["online_printers"] == 1
    assert summary["offline_printers"] == 0


def test_http_partner_cannot_toggle_other_partner_customer_portal(http_context):
    client, db, _, _, _, own, outsider, _ = http_context
    response = client.patch(
        f"/api/v1/partners/companies/{outsider.id}/customer-portal",
        json={"enabled": True},
    )
    assert response.status_code == 403
    assert db.get(Company, outsider.id).customer_portal_enabled is False


def test_http_partner_my_companies_excludes_other_partner(http_context):
    client, _, _, _, _, own, outsider, _ = http_context
    response = client.get("/api/v1/partners/my-companies")
    assert response.status_code == 200, response.text
    ids = {company["id"] for company in response.json()}
    assert own.id in ids
    assert outsider.id not in ids


def test_http_legacy_integration_excludes_inactive_unassigned_tenant(http_context, monkeypatch):
    client, db, _, _, _, own, outsider, _ = http_context
    own.partner_id = None
    own.active = False
    db.flush()
    monkeypatch.delenv("TALVOA_INTEGRATION_SCOPED_KEYS", raising=False)
    monkeypatch.setenv("TALVOA_INTEGRATION_KEY", "legacy-test-" + "c" * 40)
    headers = {"X-Talvoa-Integration-Key": "legacy-test-" + "c" * 40}
    response = client.get("/api/v1/integration/companies", headers=headers)
    assert response.status_code == 200, response.text
    assert own.uuid not in {row["uuid"] for row in response.json()}
    status = client.get("/api/v1/integration/status", headers=headers)
    assert status.status_code == 200, status.text
    assert status.json()["companies"] == 0
    assert client.get(f"/api/v1/integration/companies/{own.uuid}", headers=headers).status_code == 403


def test_http_scoped_integration_key_does_not_expose_other_tenant_details(http_context, monkeypatch):
    """Every company-detail route must reject cross-tenant scoped credentials."""
    import json
    client, _, _, _, _, own, outsider, _ = http_context
    key = "cross-tenant-regression-" + "d" * 40
    monkeypatch.setenv("TALVOA_INTEGRATION_SCOPED_KEYS", json.dumps([
        {"company_uuid": own.uuid, "key": key},
    ]))
    headers = {"X-Talvoa-Integration-Key": key}
    suffixes = (
        "",
        "/printers",
        "/users",
        "/alerts",
        "/organization",
        "/usage/report",
        "/usage/daily",
    )
    for suffix in suffixes:
        response = client.get(
            f"/api/v1/integration/companies/{outsider.uuid}{suffix}",
            headers=headers,
        )
        assert response.status_code == 403, (suffix, response.status_code, response.text)


def test_http_inactive_partner_membership_revokes_portfolio_access(http_context):
    """Removing partner membership must immediately revoke access to all tenants."""
    client, db, _, _, member, own, _, partner = http_context
    membership = db.query(PartnerMembership).filter(
        PartnerMembership.user_id == member.id,
        PartnerMembership.partner_id == partner.id,
    ).one()
    membership.active = False
    db.flush()
    assert client.get("/api/v1/partners/my-companies").status_code == 403
    assert client.get("/api/v1/partners/portfolio-summary").status_code == 403
    assert client.get(f"/api/v1/partners/companies/{own.id}/overview").status_code == 403


def test_http_inactive_partner_revokes_portfolio_access(http_context):
    """A disabled partner cannot access portfolio even with an active membership."""
    client, db, _, _, _, own, _, partner = http_context
    partner.active = False
    db.flush()
    assert client.get("/api/v1/partners/my-companies").status_code == 403
    assert client.get("/api/v1/partners/portfolio-summary").status_code == 403
    assert client.get(f"/api/v1/partners/companies/{own.id}/printers").status_code == 403


def test_http_platform_can_suspend_and_reactivate_partner(http_context):
    client, db, identity, admin, member, own, outsider, partner = http_context
    path = f"/api/v1/partners/directory/{partner.id}/status"
    assert client.patch(path, json={"active": False}).status_code == 403
    identity["user"] = admin
    response = client.patch(path, json={"active": False})
    assert response.status_code == 200, response.text
    assert response.json()["active"] is False
    assert db.get(Partner, partner.id).active is False
    identity["user"] = member
    assert client.get("/api/v1/partners/my-companies").status_code == 403
    assert client.get(f"/api/v1/partners/companies/{own.id}/overview").status_code == 403
    identity["user"] = admin
    response = client.patch(path, json={"active": True})
    assert response.status_code == 200, response.text
    assert response.json()["active"] is True
    identity["user"] = member
    assert client.get(f"/api/v1/partners/companies/{own.id}/overview").status_code == 200


def test_http_partner_status_unknown_partner_returns_404(http_context):
    client, _, identity, admin, *_ = http_context
    identity["user"] = admin
    response = client.patch("/api/v1/partners/directory/999999/status", json={"active": False})
    assert response.status_code == 404


def test_http_platform_creates_named_partner_user_with_isolated_company(http_context):
    client, db, identity, admin, member, own, outsider, partner = http_context
    path = f"/api/v1/partners/directory/{partner.id}/users"
    payload = {
        "name": "Gestora SupriTech",
        "email": "gestora.supritech@example.com",
        "password": "ExampleOnly-StrongPassword-123",
        "role": "partner_admin",
    }
    assert client.post(path, json=payload).status_code == 403
    identity["user"] = admin
    response = client.post(path, json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["role"] == "partner_admin"
    assert data["partner_id"] == partner.id
    assert "password" not in data
    created = db.get(User, data["id"])
    assert created.company_id not in (own.id, outsider.id)
    assert created.password_hash != payload["password"]
    membership = db.query(PartnerMembership).filter(
        PartnerMembership.user_id == created.id,
        PartnerMembership.partner_id == partner.id,
    ).one()
    assert membership.role == "partner_admin"
    assert client.post(path, json=payload).status_code == 409


def test_http_partner_user_rejects_weak_password(http_context):
    client, _, identity, admin, _, _, _, partner = http_context
    identity["user"] = admin
    response = client.post(f"/api/v1/partners/directory/{partner.id}/users", json={
        "name": "Gestora SupriTech",
        "email": "new@example.test",
        "password": "short",
        "role": "partner_admin",
    })
    assert response.status_code == 422


def test_http_partner_membership_revocation_is_scoped_and_admin_only(http_context):
    client, db, identity, admin, member, own, outsider, partner = http_context
    membership = db.query(PartnerMembership).filter(
        PartnerMembership.partner_id == partner.id,
        PartnerMembership.user_id == member.id,
    ).first()
    assert membership is not None
    path = f"/api/v1/partners/directory/{partner.id}/members/{membership.id}/status"
    assert client.patch(path, json={"active": False}).status_code == 403
    identity["user"] = admin
    response = client.patch(path, json={"active": False})
    assert response.status_code == 200, response.text
    db.refresh(membership)
    assert membership.active is False
    assert db.get(User, member.id).active is True
    assert client.patch(
        f"/api/v1/partners/directory/{partner.id + 999}/members/{membership.id}/status",
        json={"active": True},
    ).status_code == 404
    response = client.patch(path, json={"active": True})
    assert response.status_code == 200, response.text
    db.refresh(membership)
    assert membership.active is True


def test_http_partner_member_directory_does_not_expose_secrets(http_context):
    client, _, identity, admin, member, _, _, partner = http_context
    path = f"/api/v1/partners/directory/{partner.id}/members"
    assert client.get(path).status_code == 403
    identity["user"] = admin
    response = client.get(path)
    assert response.status_code == 200, response.text
    entries = response.json()
    assert any(entry["user_id"] == member.id for entry in entries)
    assert all("password_hash" not in entry and "session_version" not in entry for entry in entries)


def test_http_partner_users_share_identity_tenant_without_using_customer_tenant(http_context):
    client, db, identity, admin, _, own, outsider, partner = http_context
    identity["user"] = admin
    path = f"/api/v1/partners/directory/{partner.id}/users"
    company_ids = []
    for suffix in ("first", "second"):
        response = client.post(path, json={
            "name": f"Partner User {suffix}",
            "email": f"partner-{suffix}@example.com",
            "password": "ExampleOnly-StrongPassword-123",
            "role": "partner_admin",
        })
        assert response.status_code == 201, response.text
        user = db.get(User, response.json()["id"])
        company_ids.append(user.company_id)
    assert company_ids[0] == company_ids[1]
    assert company_ids[0] not in (own.id, outsider.id)
    identity_company = db.get(Company, company_ids[0])
    assert identity_company.partner_id == partner.id


def test_http_partner_user_cannot_be_created_under_suspended_partner(http_context):
    client, db, identity, admin, _, _, _, partner = http_context
    identity["user"] = admin
    partner.active = False
    db.commit()
    response = client.post(f"/api/v1/partners/directory/{partner.id}/users", json={
        "name": "Suspended Partner User",
        "email": "suspended-partner@example.com",
        "password": "ExampleOnly-StrongPassword-123",
        "role": "partner_admin",
    })
    assert response.status_code == 404, response.text
    assert db.query(User).filter(User.email == "suspended-partner@example.com").count() == 0


def test_http_partner_user_rejects_invalid_role_without_creating_identity(http_context):
    client, db, identity, admin, _, _, _, partner = http_context
    identity["user"] = admin
    response = client.post(f"/api/v1/partners/directory/{partner.id}/users", json={
        "name": "Invalid Partner Role",
        "email": "invalid-partner-role@example.com",
        "password": "ExampleOnly-StrongPassword-123",
        "role": "platform_admin",
    })
    assert response.status_code == 422, response.text
    assert db.query(User).filter(User.email == "invalid-partner-role@example.com").count() == 0


def test_http_partner_member_cannot_be_restored_when_partner_suspended(http_context):
    client, db, identity, admin, member, _, _, partner = http_context
    identity["user"] = admin
    membership = db.query(PartnerMembership).filter(
        PartnerMembership.partner_id == partner.id,
        PartnerMembership.user_id == member.id,
    ).one()
    membership.active = False
    partner.active = False
    db.commit()
    path = f"/api/v1/partners/directory/{partner.id}/members/{membership.id}/status"
    response = client.patch(path, json={"active": True})
    assert response.status_code == 409, response.text
    db.refresh(membership)
    assert membership.active is False
