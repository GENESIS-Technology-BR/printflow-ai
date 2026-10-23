"""Offline checks for Neon Free quota monitor. No API key needed."""
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "ops" / "neon_free_usage_monitor.py"
spec = importlib.util.spec_from_file_location("neon_free_usage_monitor", SCRIPT)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)

class NeonMonitorTests(unittest.TestCase):
    def test_project_ids(self):
        self.assertEqual(len(monitor.PROJECTS), 2)
        self.assertEqual(monitor.PROJECTS["talvoa-supritech-homolog"], "red-hat-77865204")

    def test_quota_limits(self):
        self.assertEqual(monitor.LIMITS["Compute CU-hours"], ("compute_time_seconds", 360000))
        self.assertEqual(monitor.LIMITS["Storage GB"], ("logical_size", 1000000000))
        self.assertEqual(monitor.LIMITS["Transfer GB"], ("data_transfer_bytes", 5000000000))

    def test_missing_secret_fails_closed(self):
        with patch.dict("os.environ", {"NEON_API_KEY": ""}):
            self.assertEqual(monitor.main(), 2)

if __name__ == "__main__":
    unittest.main()
