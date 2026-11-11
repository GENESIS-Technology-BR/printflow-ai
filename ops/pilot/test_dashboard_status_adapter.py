import unittest
from datetime import datetime, timedelta, timezone
from dashboard_status_adapter import build_dashboard_response


class DashboardStatusAdapterTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)

    def test_card_contract_and_printer_details(self):
        rows = [
            {"tenant_id": "guerra", "printer_id": "printer-1",
             "agent_last_seen": self.now - timedelta(minutes=1),
             "printer_last_seen": self.now - timedelta(minutes=1)},
            {"tenant_id": "guerra", "printer_id": "printer-2",
             "agent_last_seen": self.now - timedelta(minutes=16),
             "printer_last_seen": self.now - timedelta(minutes=1)},
        ]
        result = build_dashboard_response(
            authenticated_tenant_id="guerra", requested_tenant_id="guerra",
            authorized_printer_rows=rows, now=self.now,
        )
        self.assertEqual(result["cards"], {
            "total": 2, "online": 1, "attention": 0, "critical": 1, "unknown": 0,
        })
        self.assertEqual(len(result["printers"]), 2)
        self.assertEqual(result["policy_version"], "pilot-v1")

    def test_cross_tenant_denied(self):
        with self.assertRaises(PermissionError):
            build_dashboard_response(
                authenticated_tenant_id="guerra", requested_tenant_id="other",
                authorized_printer_rows=[], now=self.now,
            )


if __name__ == "__main__":
    unittest.main()
