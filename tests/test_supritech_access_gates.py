"""Functional authorization tests with synthetic tenants; no database or network.

Run: python -m unittest tests.test_supritech_access_gates -v
"""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException
from backend.modules.partners.access import (
    require_partner_company_access,
    require_legacy_company_portal_access,
)


def user(role, company_id=10, user_id=7):
    return SimpleNamespace(id=user_id, role=role, company_id=company_id)


def company(company_id=10, partner_id=100, portal=False):
    return SimpleNamespace(
        id=company_id, partner_id=partner_id,
        customer_portal_enabled=portal, active=True,
    )


def db_for(company_record, memberships=()):
    """Return a query-chain double; model-specific results are deterministic."""
    db = MagicMock()
    def query(model):
        result = MagicMock()
        name = model.__name__
        if name == "Company":
            result.filter.return_value.first.return_value = company_record
        elif name == "PartnerMembership":
            result.filter.return_value.join.return_value.filter.return_value.all.return_value = list(memberships)
        else:
            raise AssertionError(f"Unexpected query: {name}")
        return result
    db.query.side_effect = query
    return db


class PartnerCompanyAccessGates(unittest.TestCase):
    def assert_denied(self, expected_status, callback):
        with self.assertRaises(HTTPException) as context:
            callback()
        self.assertEqual(context.exception.status_code, expected_status)

    def test_partner_admin_can_read_and_write_own_company(self):
        tenant = company()
        membership = SimpleNamespace(role="partner_admin")
        db = db_for(tenant, [membership])
        actor = user("partner_admin")
        self.assertIs(require_partner_company_access(db, actor, 10), tenant)
        self.assertIs(require_partner_company_access(db, actor, 10, write=True), tenant)

    def test_partner_viewer_can_read_but_cannot_write(self):
        tenant = company()
        db = db_for(tenant, [SimpleNamespace(role="partner_viewer")])
        actor = user("partner_viewer")
        self.assertIs(require_partner_company_access(db, actor, 10), tenant)
        self.assert_denied(403, lambda: require_partner_company_access(db, actor, 10, write=True))

    def test_other_partner_without_membership_is_denied(self):
        db = db_for(company(company_id=20, partner_id=200))
        actor = user("partner_admin", company_id=10)
        self.assert_denied(403, lambda: require_partner_company_access(db, actor, 20))

    def test_customer_cannot_enter_other_tenant_even_if_portal_enabled(self):
        db = db_for(company(company_id=20, partner_id=200, portal=True))
        actor = user("client", company_id=10)
        self.assert_denied(403, lambda: require_partner_company_access(db, actor, 20))

    def test_customer_portal_requires_opt_in(self):
        actor = user("client", company_id=10)
        disabled = db_for(company(portal=False))
        self.assert_denied(403, lambda: require_partner_company_access(disabled, actor, 10))
        enabled_company = company(portal=True)
        enabled = db_for(enabled_company)
        self.assertIs(require_partner_company_access(enabled, actor, 10), enabled_company)
        self.assert_denied(403, lambda: require_partner_company_access(enabled, actor, 10, write=True))

    def test_missing_company_returns_404(self):
        self.assert_denied(404, lambda: require_partner_company_access(db_for(None), user("client"), 999))

    def test_platform_admin_can_access_any_existing_company(self):
        tenant = company(company_id=20, partner_id=200)
        db = db_for(tenant)
        self.assertIs(require_partner_company_access(db, user("platform_admin"), 20, write=True), tenant)

    def test_legacy_portal_denies_assigned_customer_until_enabled(self):
        actor = user("client")
        self.assert_denied(403, lambda: require_legacy_company_portal_access(db_for(company(portal=False)), actor))
        enabled = company(portal=True)
        self.assertIs(require_legacy_company_portal_access(db_for(enabled), actor), enabled)

    def test_legacy_unassigned_company_remains_accessible(self):
        tenant = company(partner_id=None)
        self.assertIs(require_legacy_company_portal_access(db_for(tenant), user("client")), tenant)


if __name__ == "__main__":
    unittest.main()
