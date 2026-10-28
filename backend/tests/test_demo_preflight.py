"""Regression tests for the offline SupriTech demo preflight."""
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "ops" / "demo_preflight.py"


class DemoPreflightTests(unittest.TestCase):
    def test_preflight_matches_documented_acceptance_state(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        matrix = (REPO / "docs/qa/talvoa-1.0-homologacao.md").read_text(encoding="utf-8")
        rows = [line.split("|") for line in matrix.splitlines() if line.startswith("| H")]
        expected_ids = {f"H{i:02d}" for i in range(1, 15)}
        found_ids = [row[1].strip() for row in rows if len(row) >= 5]
        accepted = (
            len(rows) == 14
            and len(found_ids) == 14
            and set(found_ids) == expected_ids
            and all(row[4].strip().casefold() == "aprovado" for row in rows)
        )
        self.assertEqual(result.returncode, 0 if accepted else 1, result.stdout + result.stderr)
        if not accepted:
            self.assertIn("NOT CLEARED", result.stdout)
        else:
            self.assertIn("Source preflight passed", result.stdout)

    def test_preflight_is_read_only(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("requests.", "urllib.request", "subprocess.", "os.system(", "psycopg", "sqlalchemy"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
