import unittest
from datetime import datetime, timedelta, timezone
from printer_status_policy import printer_operational_state


class PrinterStatusTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)

    def seen(self, minutes):
        return self.now - timedelta(minutes=minutes)

    def test_both_fresh(self):
        self.assertEqual(printer_operational_state(self.seen(1), self.seen(2), self.now), "online")

    def test_agent_offline_overrides_printer_freshness(self):
        self.assertEqual(printer_operational_state(self.seen(16), self.seen(1), self.now), "offline")

    def test_printer_offline_with_agent_online(self):
        self.assertEqual(printer_operational_state(self.seen(1), self.seen(16), self.now), "offline")

    def test_delayed_agent(self):
        self.assertEqual(printer_operational_state(self.seen(8), self.seen(1), self.now), "delayed")

    def test_delayed_printer(self):
        self.assertEqual(printer_operational_state(self.seen(1), self.seen(8), self.now), "delayed")

    def test_no_agent_data(self):
        self.assertEqual(printer_operational_state(None, self.seen(1), self.now), "unknown")

    def test_no_printer_data(self):
        self.assertEqual(printer_operational_state(self.seen(1), None, self.now), "unknown")

    def test_future_printer_timestamp(self):
        self.assertEqual(printer_operational_state(self.seen(1), self.now + timedelta(seconds=1), self.now), "unknown")


if __name__ == "__main__":
    unittest.main()
