"""Regression tests for the offline SupriTech demo preflight."""
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "ops" / "demo_preflight.py"


class DemoPreflightTests(unittest.TestCase):
    def test_current_homologation_is_not_cleared(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("NOT CLEARED", result.stdout)
        self.assertIn("H01", result.stdout)
        self.assertIn("H09", result.stdout)
        self.assertIn("H14", result.stdout)

    def test_preflight_is_read_only(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("requests.", "urllib.request", "subprocess.", "os.system(", "psycopg", "sqlalchemy"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
