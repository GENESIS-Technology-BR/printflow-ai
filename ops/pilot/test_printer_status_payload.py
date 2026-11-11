import unittest
from datetime import datetime, timedelta, timezone
from printer_status_payload import printer_status_payload


class StatusPayloadTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)

    def test_online_serializable_projection(self):
        result = printer_status_payload(
            printer_id="printer-01",
            agent_last_seen=self.now - timedelta(minutes=1),
            printer_last_seen=self.now - timedelta(minutes=2),
            now=self.now,
        )
        self.assertEqual(result["operational_status"], "online")
        self.assertEqual(result["policy_version"], "pilot-v1")
        self.assertEqual(result["printer_id"], "printer-01")
        self.assertTrue(result["evaluated_at"].endswith("+00:00"))

    def test_offline_agent_propagates_to_payload(self):
        result = printer_status_payload(
            printer_id="printer-02",
            agent_last_seen=self.now - timedelta(minutes=20),
            printer_last_seen=self.now - timedelta(minutes=1),
            now=self.now,
        )
        self.assertEqual(result["operational_status"], "offline")

    def test_missing_printer_id_rejected(self):
        with self.assertRaises(ValueError):
            printer_status_payload(
                printer_id=" ", agent_last_seen=None, printer_last_seen=None, now=self.now
            )

    def test_no_telemetry_returns_unknown(self):
        result = printer_status_payload(
            printer_id="printer-03", agent_last_seen=None, printer_last_seen=None, now=self.now
        )
        self.assertEqual(result["operational_status"], "unknown")


if __name__ == "__main__":
    unittest.main()
