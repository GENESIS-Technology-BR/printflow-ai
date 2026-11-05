"""Offline unit tests for portable TALVOA #99 backup locator and SHA pin."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "ops" / "talvoa_restore_m99_preflight.py"
spec = importlib.util.spec_from_file_location("talvoa_m99_preflight", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Mission99PortablePreflightTests(unittest.TestCase):
    def test_detects_new_windows_profile_using_environment(self):
        home = Path("C:/Users/AnotherUser")
        paths = module.candidates(None, home, {"OneDrive": "C:/Users/AnotherUser/OneDrive"})
        self.assertIn(Path("C:/Users/AnotherUser/OneDrive/TALVOA-Backups") / module.BACKUP_NAME, paths)
        self.assertNotIn("jandi", str(paths).lower())

    def test_rejects_changed_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / module.BACKUP_NAME
            path.write_bytes(b"synthetic data, not a real backup")
            errors = module.assess_file(path)
            self.assertTrue(any("Tamanho" in e for e in errors))
            self.assertTrue(any("SHA-256" in e for e in errors))

    def test_missing_backup_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / module.BACKUP_NAME
            self.assertIn("nao encontrado", module.assess_file(path)[0])

    def test_backup_identifier_is_fixed(self):
        self.assertEqual(len(module.BACKUP_SHA256), 64)
        self.assertTrue(module.BACKUP_NAME.endswith(".dump.aesgcm"))


if __name__ == "__main__":
    unittest.main()
