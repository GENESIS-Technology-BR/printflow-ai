"""Synthetic partner scope regression tests."""
import unittest
from backend.modules.partners.router import my_partner_companies
from tests.test_supritech_access_sqlite import SupritechSqliteAuthorization


class PartnerScopeTests(SupritechSqliteAuthorization):
    def test_portfolio_excludes_other_partner_companies(self):
        companies = my_partner_companies(user=self.actor(1), db=self.db)
        ids = {item['id'] for item in companies}
        self.assertIn(10, ids)
        self.assertNotIn(20, ids)
        self.assertNotIn(30, ids)

    def test_portfolio_denied_when_membership_revoked(self):
        membership = self.db.query(__import__('backend.modules.partners.model', fromlist=['PartnerMembership']).PartnerMembership).filter_by(user_id=1, partner_id=100).one()
        membership.active = False
        self.db.flush()
        self.denied(403, lambda: my_partner_companies(user=self.actor(1), db=self.db))


if __name__ == '__main__':
    unittest.main()
