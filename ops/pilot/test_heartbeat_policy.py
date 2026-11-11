import unittest
from datetime import datetime, timedelta, timezone
from heartbeat_policy import heartbeat_state


class HeartbeatPolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)

    def test_fresh(self):
        self.assertEqual(heartbeat_state(self.now - timedelta(minutes=5), self.now), "online")

    def test_delayed(self):
        self.assertEqual(heartbeat_state(self.now - timedelta(minutes=10), self.now), "delayed")

    def test_offline(self):
        self.assertEqual(heartbeat_state(self.now - timedelta(minutes=16), self.now), "offline")

    def test_unknown(self):
        self.assertEqual(heartbeat_state(None, self.now), "unknown")

    def test_future_is_unknown(self):
        self.assertEqual(heartbeat_state(self.now + timedelta(seconds=1), self.now), "unknown")

    def test_naive_is_unknown(self):
        self.assertEqual(heartbeat_state(self.now.replace(tzinfo=None), self.now), "unknown")

    def test_invalid_policy_rejected(self):
        with self.assertRaises(ValueError):
            heartbeat_state(self.now, self.now, expected_interval_minutes=0)


if __name__ == "__main__":
    unittest.main()
