"""Offline checks: no Render connection and no customer data."""
import importlib.util
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "ops" / "talvoa_secure_backup_windows.py"
spec = importlib.util.spec_from_file_location("talvoa_backup", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BackupOfflineTests(unittest.TestCase):
    def test_accepts_only_dedicated_render_database(self):
        env = module.parse_source(
            "postgresql://talvoa_supritech_admin_v2:p%40ss@dpg-db7rsb25b2lc739g0img-a.oregon-postgres.render.com:5432/"
            "talvoa_supritech_homolog_db"
        )
        self.assertEqual(env["PGPASSWORD"], "p@ss")
        self.assertEqual(env["PGSSLMODE"], "require")
        self.assertEqual(env["PGDATABASE"], module.DB_NAME)

    def test_rejects_wrong_database_and_host(self):
        cases = (
            "postgresql://talvoa_supritech_admin_v2:p@dpg-db7rsb25b2lc739g0img-a.oregon-postgres.render.com/printflow_production",
            "postgresql://u:p@attacker.example.com/talvoa_supritech_homolog_db",
            "http://talvoa_supritech_admin_v2:p@dpg-db7rsb25b2lc739g0img-a.oregon-postgres.render.com/talvoa_supritech_homolog_db",
        )
        for url in cases:
            with self.subTest(url=url), self.assertRaises(ValueError):
                module.parse_source(url)


    def test_rejects_same_db_on_wrong_render_host_or_user_or_port(self):
        host = "dpg-db7rsb25b2lc739g0img-a.oregon-postgres.render.com"
        name = module.DB_NAME
        user = module.DB_USER
        cases = (
            f"postgresql://{user}:p@another-db.oregon-postgres.render.com/{name}",
            f"postgresql://different_user:p@{host}/{name}",
            f"postgresql://{user}:p@{host}:5433/{name}",
            f"postgresql://{user}:p@{host}.attacker.example.com/{name}",
        )
        for url in cases:
            with self.subTest(url=url), self.assertRaises(ValueError):
                module.parse_source(url)

    def test_clients_must_both_be_postgresql_16(self):
        with mock.patch.object(module.shutil, "which", return_value=sys.executable):
            with mock.patch.object(module.subprocess, "run") as run:
                run.side_effect = [
                    mock.Mock(stdout="pg_dump (PostgreSQL) 16.15"),
                    mock.Mock(stdout="pg_restore (PostgreSQL) 15.8"),
                ]
                with self.assertRaises(RuntimeError):
                    module.require_clients()
            with mock.patch.object(module.subprocess, "run") as run:
                run.side_effect = [
                    mock.Mock(stdout="pg_dump (PostgreSQL) 16.15"),
                    mock.Mock(stdout="pg_restore (PostgreSQL) 16.15"),
                ]
                paths = module.require_clients()
                self.assertEqual(paths["pg_dump"], str(pathlib.Path(sys.executable).resolve()))
                self.assertEqual(paths["pg_restore"], str(pathlib.Path(sys.executable).resolve()))
                self.assertEqual(run.call_args_list[0].args[0][0], paths["pg_dump"])

    def test_removes_all_inherited_libpq_overrides(self):
        sample = {
            "PGHOSTADDR": "203.0.113.10",
            "PGSERVICE": "unexpected-service",
            "PGOPTIONS": "other-options",
            "PGUSER": "untrusted",
            "PATH": "trusted-path",
        }
        verified = module.parse_source(
            "postgresql://talvoa_supritech_admin_v2:p@"
            "dpg-db7rsb25b2lc739g0img-a.oregon-postgres.render.com/"
            "talvoa_supritech_homolog_db"
        )
        with mock.patch.dict(module.os.environ, sample, clear=True):
            env = module.pg_environment(verified)
        self.assertEqual(env["PGHOST"], module.DB_HOST)
        self.assertEqual(env["PGUSER"], module.DB_USER)
        self.assertEqual(env["PATH"], "trusted-path")
        for key in ("PGHOSTADDR", "PGSERVICE", "PGOPTIONS"):
            self.assertNotIn(key, env)

    def test_rejects_double_slash_database_path_and_query_overrides(self):
        host = module.DB_HOST
        user = module.DB_USER
        name = module.DB_NAME
        for url in (
            f"postgresql://{user}:p@{host}//{name}",
            f"postgresql://{user}:p@{host}/{name}?hostaddr=203.0.113.10",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                module.parse_source(url)

    def test_secret_prompt_refuses_getpass_echo_fallback(self):
        with mock.patch.object(module.getpass, "getpass") as prompt:
            prompt.side_effect = module.getpass.GetPassWarning("terminal unavailable")
            with self.assertRaisesRegex(RuntimeError, "Secure secret input unavailable"):
                module.read_secret("Hidden secret: ")
        with mock.patch.object(module.getpass, "getpass", return_value="synthetic-only"):
            self.assertEqual(module.read_secret("Hidden secret: "), "synthetic-only")

    def test_url_parser_does_not_expose_secrets_in_exceptions(self):
        secret = "privateSyntheticPassShouldNotAppear"
        test_urls = (
            f"postgresql://user:{secret}@[invalid-host/db",
            f"postgresql://user:{secret}@dpg-db7rsb25b2lc739g0img-a.oregon-postgres.render.com:badport/talvoa_supritech_homolog_db",
        )
        for url in test_urls:
            with self.subTest(malformed=True), self.assertRaises(ValueError) as caught:
                module.parse_source(url)
            self.assertNotIn(secret, str(caught.exception))
            self.assertNotIn(url, str(caught.exception))

    def test_url_parser_rejects_control_characters_including_percent_encoded(self):
        prefix = (
            "postgresql://talvoa_supritech_admin_v2:p"
        )
        suffix = (
            "@dpg-db7rsb25b2lc739g0img-a.oregon-postgres.render.com/"
            "talvoa_supritech_homolog_db"
        )
        for separator in (chr(10), chr(13), chr(9), "%0A", "%0D", "%00", "%7F"):
            with self.subTest(separator=repr(separator)), self.assertRaises(ValueError):
                module.parse_source(prefix + separator + suffix)

if __name__ == "__main__":
    unittest.main()
