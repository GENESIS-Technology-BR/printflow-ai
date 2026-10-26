"""Unit tests for the isolated tenant authorization reference policy.

Run: python -m unittest discover -s ops/robot-plans -p 'test_tenant_policy.py'
"""
import unittest
from tenant_policy_reference import Actor, may_access_tenant


class TenantPolicyTests(unittest.TestCase):
    def test_client_reads_own_tenant(self):
        actor = Actor(role="client", company_id="guerra")
        self.assertTrue(may_access_tenant(actor, "guerra", mutate=False))

    def test_client_cannot_mutate_even_own_tenant(self):
        actor = Actor(role="client", company_id="guerra")
        self.assertFalse(may_access_tenant(actor, "guerra", mutate=True))

    def test_client_cannot_read_other_tenant(self):
        actor = Actor(role="client", company_id="guerra")
        self.assertFalse(may_access_tenant(actor, "supritech", mutate=False))

    def test_admin_requires_explicit_authorized_tenant(self):
        actor = Actor(role="platform_admin", company_id="guerra",
                      authorized_tenants=frozenset({"guerra"}))
        self.assertTrue(may_access_tenant(actor, "guerra", mutate=True))
        self.assertFalse(may_access_tenant(actor, "supritech", mutate=True))
        self.assertFalse(may_access_tenant(actor, None, mutate=True))

    def test_unknown_role_is_denied(self):
        self.assertFalse(may_access_tenant(Actor(role="unknown", company_id="guerra"),
                                          "guerra", mutate=False))

    def test_blank_tenant_is_denied(self):
        actor = Actor(role="platform_admin", company_id="guerra",
                      authorized_tenants=frozenset({"guerra"}))
        self.assertFalse(may_access_tenant(actor, " ", mutate=True))


if __name__ == "__main__":
    unittest.main()
