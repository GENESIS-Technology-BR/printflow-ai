"""Real SQLAlchemy tenant authorization tests using in-memory synthetic SQLite.

No production connection, credentials, migrations or HTTP server are used.
Run: python -m unittest discover -s tests -p test_supritech_access_sqlite.py -v
"""
import unittest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database.connection import Base
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.partners.model import Partner, PartnerMembership
from backend.modules.partners.access import (
    require_partner_company_access,
    require_legacy_company_portal_access,
)


class SupritechSqliteAuthorization(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[
                Partner.__table__,
                Company.__table__,
                User.__table__,
                PartnerMembership.__table__,
            ],
        )
        self.db = Session(self.engine)
        self.db.add_all([
            Partner(id=100, name="Synthetic SupriTech", active=True),
            Partner(id=200, name="Other synthetic reseller", active=True),
            Company(id=10, name="Synthetic Guerra", partner_id=100, active=True, customer_portal_enabled=False),
            Company(id=20, name="Unrelated synthetic customer", partner_id=200, active=True, customer_portal_enabled=True),
            Company(id=30, name="Legacy synthetic customer", partner_id=None, active=True),
        ])
        self.db.flush()
        self.db.add_all([
            User(id=1, company_id=10, name="Partner admin", email="partner@example.invalid", password_hash="synthetic", role="partner_admin"),
            User(id=2, company_id=10, name="Partner viewer", email="viewer@example.invalid", password_hash="synthetic", role="partner_viewer"),
            User(id=3, company_id=10, name="Customer", email="customer@example.invalid", password_hash="synthetic", role="client"),
            User(id=4, company_id=10, name="Platform", email="platform@example.invalid", password_hash="synthetic", role="platform_admin"),
            User(id=5, company_id=30, name="Legacy", email="legacy@example.invalid", password_hash="synthetic", role="client"),
        ])
        self.db.flush()
        self.db.add_all([
            PartnerMembership(partner_id=100, user_id=1, role="partner_admin", active=True),
            PartnerMembership(partner_id=100, user_id=2, role="partner_viewer", active=True),
            PartnerMembership(partner_id=200, user_id=2, role="partner_admin", active=False),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def actor(self, user_id):
        return self.db.get(User, user_id)

    def denied(self, code, func):
        with self.assertRaises(HTTPException) as caught:
            func()
        self.assertEqual(caught.exception.status_code, code)

    def test_partner_admin_accesses_own_tenant(self):
        self.assertEqual(require_partner_company_access(self.db, self.actor(1), 10, write=True).id, 10)

    def test_partner_admin_cannot_access_unrelated_partner(self):
        self.denied(403, lambda: require_partner_company_access(self.db, self.actor(1), 20))

    def test_partner_viewer_cannot_write(self):
        self.assertEqual(require_partner_company_access(self.db, self.actor(2), 10).id, 10)
        self.denied(403, lambda: require_partner_company_access(self.db, self.actor(2), 10, write=True))

    def test_inactive_other_partner_membership_does_not_grant_access(self):
        self.denied(403, lambda: require_partner_company_access(self.db, self.actor(2), 20, write=True))

    def test_customer_cannot_access_other_tenant(self):
        self.denied(403, lambda: require_partner_company_access(self.db, self.actor(3), 20))

    def test_customer_requires_portal_opt_in(self):
        self.denied(403, lambda: require_legacy_company_portal_access(self.db, self.actor(3)))
        self.db.get(Company, 10).customer_portal_enabled = True
        self.db.flush()
        self.assertEqual(require_legacy_company_portal_access(self.db, self.actor(3)).id, 10)
        self.denied(403, lambda: require_partner_company_access(self.db, self.actor(3), 10, write=True))

    def test_legacy_unassigned_customer_remains_supported(self):
        self.assertEqual(require_legacy_company_portal_access(self.db, self.actor(5)).id, 30)

    def test_platform_admin_is_explicitly_privileged(self):
        self.assertEqual(require_partner_company_access(self.db, self.actor(4), 20, write=True).id, 20)

    def test_missing_company_returns_404(self):
        self.denied(404, lambda: require_partner_company_access(self.db, self.actor(1), 999))

    def test_inactive_company_denied(self):
        self.db.get(Company, 10).active = False
        self.db.flush()
        self.denied(404, lambda: require_partner_company_access(self.db, self.actor(1), 10))


if __name__ == "__main__":
    unittest.main()
