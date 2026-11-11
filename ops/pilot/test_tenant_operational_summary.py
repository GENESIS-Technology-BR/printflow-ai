import unittest
from datetime import datetime, timedelta, timezone
from tenant_operational_summary import tenant_operational_summary


class TenantOperationalSummaryTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)

    def record(self, printer_id, agent_age, printer_age, tenant="guerra"):
        return {
            "tenant_id": tenant, "printer_id": printer_id,
            "agent_last_seen": None if agent_age is None else self.now - timedelta(minutes=agent_age),
            "printer_last_seen": None if printer_age is None else self.now - timedelta(minutes=printer_age),
        }

    def test_counts_and_tenant_isolation(self):
        rows = [
            self.record("p1", 1, 1),
            self.record("p2", 8, 1),
            self.record("p3", 20, 1),
            self.record("p4", None, None),
            self.record("other", 1, 1, "other"),
        ]
        result = tenant_operational_summary(
            authorized_tenant_id="guerra", requested_tenant_id="guerra",
            printers=rows, now=self.now,
        )
        self.assertEqual(result["total"], 4)
        self.assertEqual(result["counts"], {"online": 1, "delayed": 1, "offline": 1, "unknown": 1})
        self.assertEqual(result["attention"], 1)
        self.assertEqual(result["critical"], 1)
        self.assertEqual(result["unverified"], 1)

    def test_empty_inventory(self):
        result = tenant_operational_summary(
            authorized_tenant_id="guerra", requested_tenant_id="guerra",
            printers=[], now=self.now,
        )
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["critical"], 0)

    def test_cross_tenant_rejected(self):
        with self.assertRaises(PermissionError):
            tenant_operational_summary(
                authorized_tenant_id="guerra", requested_tenant_id="other",
                printers=[], now=self.now,
            )


if __name__ == "__main__":
    unittest.main()
