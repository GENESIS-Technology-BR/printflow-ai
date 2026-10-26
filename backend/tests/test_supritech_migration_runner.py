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

    def test_refuse_existing_backup_before_dump(self):
        import sys
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            backup = Path(directory) / "existing.dump"
            backup.write_bytes(b"existing")
            with patch.dict(os.environ, {
                "TALVOA_SOURCE_DATABASE_URL": SRC,
                "TALVOA_TARGET_DATABASE_URL": DST,
                "TALVOA_MIGRATION_APPROVED": "supritech-homolog",
                "TALVOA_EXPECTED_NEON_HOST": runner.database(DST)[1],
            }), patch.object(sys, "argv", ["migration", "--apply", "--backup", str(backup)]), patch.object(
                runner.shutil, "which", return_value="/usr/bin/psql"
            ), patch.object(runner.subprocess, "run") as execute:
                execute.return_value.stdout = "0\\n"
                with self.assertRaises(SystemExit):
                    runner.main()
                self.assertEqual(backup.read_bytes(), b"existing")
                self.assertEqual(execute.call_count, 1)

    def test_refuse_symlink_backup_before_dump(self):
        import sys
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            existing = Path(directory) / "protected.dump"
            existing.write_bytes(b"protected")
            link = Path(directory) / "link.dump"
            link.symlink_to(existing)
            with patch.dict(os.environ, {
                "TALVOA_SOURCE_DATABASE_URL": SRC,
                "TALVOA_TARGET_DATABASE_URL": DST,
                "TALVOA_MIGRATION_APPROVED": "supritech-homolog",
                "TALVOA_EXPECTED_NEON_HOST": runner.database(DST)[1],
            }), patch.object(sys, "argv", ["migration", "--apply", "--backup", str(link)]), patch.object(
                runner.shutil, "which", return_value="/usr/bin/psql"
            ), patch.object(runner.subprocess, "run") as execute:
                execute.return_value.stdout = "0\\n"
                with self.assertRaises(SystemExit):
                    runner.main()
                self.assertEqual(existing.read_bytes(), b"protected")
                self.assertEqual(execute.call_count, 1)

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
