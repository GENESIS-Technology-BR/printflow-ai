"""Synthetic-only AES-GCM backup integrity tests; no DB/network access."""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

OPS = pathlib.Path(__file__).resolve().parents[1] / "ops"
sys.path.insert(0, str(OPS))
from talvoa_secure_backup_windows import encrypt_dump  # noqa: E402
from talvoa_decrypt_backup_windows import decrypt_archive  # noqa: E402


class BackupCryptoOfflineTests(unittest.TestCase):
    def test_roundtrip_encryption_and_authentication(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            source = d / "synthetic.dump"
            encrypted = d / "synthetic.aesgcm"
            recovered = d / "recovered.dump"
            source.write_bytes(b"synthetic test backup" * 1200)
            passphrase = "synthetic-test-only-long-passphrase"
            encrypt_dump(source, encrypted, passphrase)
            decrypt_archive(encrypted, passphrase, None)
            decrypt_archive(encrypted, passphrase, recovered)
            self.assertEqual(source.read_bytes(), recovered.read_bytes())

    def test_corruption_and_wrong_key_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            plain = d / "synthetic.dump"
            archive = d / "synthetic.aesgcm"
            plain.write_bytes(b"synthetic only" * 150)
            encrypt_dump(plain, archive, "test-only-long-passphrase-000")
            with self.assertRaises(Exception):
                decrypt_archive(archive, "wrong-passphrase", None)
            raw = bytearray(archive.read_bytes())
            raw[-17] ^= 1
            archive.write_bytes(raw)
            with self.assertRaises(Exception):
                decrypt_archive(archive, "test-only-long-passphrase-000", None)


if __name__ == "__main__":
    unittest.main()
