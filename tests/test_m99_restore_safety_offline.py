"""Safe offline checks for mission #99 local PostgreSQL restoration."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

OPS = Path(__file__).resolve().parents[1] / "ops"
sys.path.insert(0, str(OPS))
spec = importlib.util.spec_from_file_location("talvoa_m99_restore_local", OPS / "talvoa_m99_restore_local.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Mission99RestoreSafetyTests(unittest.TestCase):
    def test_rejects_non_matching_backup_without_database_access(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / module.EXPECTED_NAME
            f.write_bytes(b"synthetic")
            with self.assertRaisesRegex(RuntimeError, "tamanho/SHA"):
                module.validate_archive(f)

    def test_new_archive_with_separate_verified_hash_and_size(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            name = "supritech-20261106T180000Z-0123456789abcdef.dump.aesgcm"
            path = Path(td) / name
            payload = b"synthetic-encrypted-file-placeholder" * 4
            path.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            module.validate_archive(path, expected_sha256=digest, expected_size=len(payload))
            with self.assertRaisesRegex(RuntimeError, "tamanho/SHA"):
                module.validate_archive(path, expected_sha256="0" * 64,
                                        expected_size=len(payload))
            with self.assertRaisesRegex(RuntimeError, "tamanho/SHA"):
                module.validate_archive(path, expected_sha256=digest,
                                        expected_size=len(payload) + 1)

    def test_archive_rejects_unexpected_filename(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "customer-unknown.dump.aesgcm"
            path.write_bytes(b"a" * 128)
            with self.assertRaisesRegex(RuntimeError, "Nome"):
                module.validate_archive(path, expected_sha256="f" * 64,
                                        expected_size=128)

    def test_libpq_configuration_is_local_only(self):
        inherited = {"PGHOSTADDR": "203.0.113.12", "PGSERVICE": "remote",
                     "PGOPTIONS": "-c some=setting", "PATH": "unchanged"}
        with mock.patch.dict(module.os.environ, inherited, clear=True):
            result = module.pg_env("synthetic-only")
        self.assertEqual(result["PGHOST"], "127.0.0.1")
        self.assertEqual(result["PGPORT"], str(module.PORT))
        self.assertEqual(result["PGDATABASE"], module.DB)
        self.assertEqual(result["PGUSER"], module.USER)
        self.assertEqual(result["PGPASSWORD"], "synthetic-only")
        self.assertEqual(result["PGSSLMODE"], "disable")
        self.assertNotIn("PGHOSTADDR", result)
        self.assertNotIn("PGSERVICE", result)
        self.assertNotIn("PGOPTIONS", result)
        self.assertEqual(result["PATH"], "unchanged")

    def test_rejects_unexpected_client_major_version(self):
        fake_binaries = {"initdb": Path("initdb.exe"),
                         "pg_ctl": Path("pg_ctl.exe"),
                         "pg_restore": Path("pg_restore.exe"),
                         "psql": Path("psql.exe"),
                         "createdb": Path("createdb.exe")}
        with mock.patch.object(module, "run", return_value="pg_restore (PostgreSQL) 17.1"):
            with self.assertRaisesRegex(RuntimeError, "16"):
                module.check_pg16(fake_binaries)

    def test_aborts_if_local_port_is_already_occupied(self):
        fake_socket = mock.MagicMock()
        fake_socket.__enter__.return_value.connect_ex.return_value = 0
        with mock.patch.object(module.socket, "socket", return_value=fake_socket):
            with self.assertRaisesRegex(RuntimeError, "Porta local ocupada"):
                module.verify_local_listener()

    def test_uses_only_localhost_when_counting_tables(self):
        local_commands = []
        def fake_run(argv, env=None, **kwargs):
            local_commands.append(argv)
            if "pg_tables" in argv[-1]:
                return "public.exemplo\n"
            return "27"
        with mock.patch.object(module, "run", side_effect=fake_run):
            tables, rows = module.count_restored_tables(Path("psql.exe"), module.pg_env("mock"))
        self.assertEqual((tables, rows), (1, 27))
        for argv in local_commands:
            self.assertIn("127.0.0.1", argv)
            self.assertIn(str(module.PORT), argv)


if __name__ == "__main__":
    unittest.main()
