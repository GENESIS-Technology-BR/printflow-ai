"""Synthetic-only AES-GCM backup integrity tests; no DB/network access."""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest
from unittest import mock

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

    def test_encryption_never_overwrites_existing_destination(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            source = d / "source.dump"
            out = d / "protected.aesgcm"
            source.write_bytes(b"synthetic")
            out.write_bytes(b"existing-backup-must-survive")
            with self.assertRaises(FileExistsError):
                encrypt_dump(source, out, "synthetic-test-password-very-long")
            self.assertEqual(out.read_bytes(), b"existing-backup-must-survive")

    def test_decryption_never_deletes_existing_partial_or_output(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            plain = d / "synthetic.dump"
            encrypted = d / "synthetic.aesgcm"
            output = d / "out.dump"
            partial = d / "out.dump.partial"
            plain.write_bytes(b"synthetic")
            encrypt_dump(plain, encrypted, "synthetic-test-password-very-long")
            partial.write_bytes(b"preexisting-protected")
            with self.assertRaises(FileExistsError):
                decrypt_archive(encrypted, "synthetic-test-password-very-long", output)
            self.assertEqual(partial.read_bytes(), b"preexisting-protected")
            partial.unlink()
            output.write_bytes(b"must-not-overwrite")
            with self.assertRaises(FileExistsError):
                decrypt_archive(encrypted, "synthetic-test-password-very-long", output)
            self.assertEqual(output.read_bytes(), b"must-not-overwrite")


if __name__ == "__main__":
    unittest.main()
