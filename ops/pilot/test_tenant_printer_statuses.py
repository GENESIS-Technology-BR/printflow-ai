import unittest
from datetime import datetime, timedelta, timezone
from tenant_printer_statuses import tenant_printer_statuses


class TenantPrinterStatusTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
        self.printers = [
            {"tenant_id": "guerra", "printer_id": "G-01",
             "agent_last_seen": self.now - timedelta(minutes=1),
             "printer_last_seen": self.now - timedelta(minutes=2)},
            {"tenant_id": "other", "printer_id": "O-01",
             "agent_last_seen": self.now, "printer_last_seen": self.now},
        ]

    def test_only_authorized_tenant_visible(self):
        result = tenant_printer_statuses(
            authorized_tenant_id="guerra", requested_tenant_id="guerra",
            printers=self.printers, now=self.now,
        )
        self.assertEqual([p["printer_id"] for p in result], ["G-01"])

    def test_cross_tenant_request_rejected(self):
        with self.assertRaises(PermissionError):
            tenant_printer_statuses(
                authorized_tenant_id="guerra", requested_tenant_id="other",
                printers=self.printers, now=self.now,
            )

    def test_missing_tenant_rejected(self):
        with self.assertRaises(PermissionError):
            tenant_printer_statuses(
                authorized_tenant_id="", requested_tenant_id="guerra",
                printers=self.printers, now=self.now,
            )

    def test_empty_tenant_inventory(self):
        self.assertEqual(tenant_printer_statuses(
            authorized_tenant_id="guerra", requested_tenant_id="guerra",
            printers=[], now=self.now,
        ), [])


if __name__ == "__main__":
    unittest.main()
