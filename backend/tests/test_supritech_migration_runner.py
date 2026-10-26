"""Offline fail-closed tests: no network, credentials or database writes."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "talvoa_supritech_migration_runner.py"
spec = importlib.util.spec_from_file_location("talvoa_migration_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

SRC = "postgresql://user:password@dpg-db7rsb25b2lc739g0img-a.oregon-postgres.render.com/talvoa_supritech_homolog_db?sslmode=require"
DST = "postgresql://owner:password@ep-example.us-east-2.aws.neon.tech/neondb?sslmode=require"

class MigrationSafetyTests(unittest.TestCase):
    def test_approved_endpoints(self):
        runner.verify(SRC, DST)

    def test_refuse_production_source(self):
        with self.assertRaises(ValueError):
            runner.verify(SRC.replace("talvoa_supritech_homolog_db?", "production?"), DST)

    def test_refuse_unapproved_source_host(self):
        with self.assertRaises(ValueError):
            runner.verify(SRC.replace("dpg-db7rsb25b2lc739g0img-a", "dpg-other"), DST)

    def test_refuse_non_neon_target(self):
        with self.assertRaises(ValueError):
            runner.verify(SRC, DST.replace(".neon.tech", ".render.com"))

    def test_refuse_unencrypted_target(self):
        with self.assertRaises(ValueError):
            runner.verify(SRC, DST.replace("sslmode=require", "sslmode=disable"))

    def test_refuse_unapproved_neon_hostname_on_apply(self):
        import sys
        with patch.dict(os.environ, {
            "TALVOA_SOURCE_DATABASE_URL": SRC,
            "TALVOA_TARGET_DATABASE_URL": DST,
            "TALVOA_MIGRATION_APPROVED": "supritech-homolog",
            "TALVOA_EXPECTED_NEON_HOST": "ep-wrong.neon.tech",
        }), patch.object(sys, "argv", ["migration", "--apply"]), patch.object(
            runner.subprocess, "run", side_effect=AssertionError("database connection attempted")
        ):
            with self.assertRaises(SystemExit) as failure:
                runner.main()
            self.assertIn("hostname", str(failure.exception).lower())

    def test_refuse_missing_expected_neon_hostname_on_apply(self):
        import sys
        with patch.dict(os.environ, {
            "TALVOA_SOURCE_DATABASE_URL": SRC,
            "TALVOA_TARGET_DATABASE_URL": DST,
            "TALVOA_MIGRATION_APPROVED": "supritech-homolog",
        }), patch.dict(os.environ, {"TALVOA_EXPECTED_NEON_HOST": ""}), patch.object(
            sys, "argv", ["migration", "--apply"]
        ), patch.object(runner.subprocess, "run", side_effect=AssertionError("database connection attempted")):
            with self.assertRaises(SystemExit):
                runner.main()

    def test_password_not_in_command_args(self):
        env = runner.pg_env(DST)
        self.assertEqual(env["PGPASSWORD"], "password")
        self.assertEqual(env["PGDATABASE"], "neondb")

    def test_dry_run_never_connects(self):
        import sys
        with patch.dict(os.environ, {
            "TALVOA_SOURCE_DATABASE_URL": SRC,
            "TALVOA_TARGET_DATABASE_URL": DST,
        }), patch.object(sys, "argv", ["migration"]), patch.object(runner.subprocess, "run", side_effect=AssertionError("network called")):
            runner.main()

if __name__ == "__main__":
    unittest.main()
