"""Offline checks: no Render connection and no customer data."""
import importlib.util
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "ops" / "talvoa_secure_backup_windows.py"
spec = importlib.util.spec_from_file_location("talvoa_backup", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BackupOfflineTests(unittest.TestCase):
    def test_accepts_only_dedicated_render_database(self):
        env = module.parse_source(
            "postgresql://limited_user:p%40ss@dpg-example.oregon-postgres.render.com:5432/"
            "talvoa_supritech_homolog_db?sslmode=require"
        )
        self.assertEqual(env["PGPASSWORD"], "p@ss")
        self.assertEqual(env["PGSSLMODE"], "require")
        self.assertEqual(env["PGDATABASE"], module.DB_NAME)

    def test_rejects_wrong_database_and_host(self):
        cases = (
            "postgresql://u:p@dpg-example.oregon-postgres.render.com/printflow_production",
            "postgresql://u:p@attacker.example.com/talvoa_supritech_homolog_db",
            "http://u:p@dpg-example.oregon-postgres.render.com/talvoa_supritech_homolog_db",
        )
        for url in cases:
            with self.subTest(url=url), self.assertRaises(ValueError):
                module.parse_source(url)

if __name__ == "__main__":
    unittest.main()
