"""Offline tests for restore comparison and safe SQL identifier quoting."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts" / "talvoa_supritech_verify_restore.py"
spec = importlib.util.spec_from_file_location("talvoa_verify_restore", path)
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)

class RestoreVerificationTests(unittest.TestCase):
    def test_identifier_escaping(self):
        self.assertEqual(verify.quote_ident('a"b'), '"a""b"')

    def test_snapshot_counts(self):
        def fake_sql(url, query):
            if "information_schema.tables" in query:
                return '["companies","printers"]'
            if '"companies"' in query:
                return "2"
            if '"printers"' in query:
                return "8"
            raise AssertionError(query)
        with patch.object(verify, "sql", side_effect=fake_sql):
            self.assertEqual(verify.snapshot("dummy"), {"companies": 2, "printers": 8})

    def test_no_network_without_secrets(self):
        import os
        with patch.dict(os.environ, {"TALVOA_SOURCE_DATABASE_URL": "", "TALVOA_TARGET_DATABASE_URL": ""}), patch.object(verify.subprocess, "run", side_effect=AssertionError("network")):
            with self.assertRaises(SystemExit):
                verify.main()

if __name__ == "__main__":
    unittest.main()
