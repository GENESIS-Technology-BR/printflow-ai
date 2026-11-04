#!/usr/bin/env python3
"""Verify/decrypt a TALVOA AES-GCM archive. NEVER targets a database.

Verification reads the ciphertext and validates its authentication tag.
Optional --output writes a plaintext .dump which MUST be stored securely and
deleted after restore into an isolated PostgreSQL instance.
"""
from __future__ import annotations

import argparse
import getpass
import os
import pathlib
import subprocess
import sys

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from talvoa_secure_backup_windows import HEADER, CHUNK, require_clients, verify_private_windows_acl


def decrypt_archive(archive: pathlib.Path, passphrase: str, output: pathlib.Path | None) -> None:
    with archive.open("rb") as stream:
        if stream.read(len(HEADER)) != HEADER:
            raise ValueError("Not a TALVOA encrypted archive")
        salt, nonce = stream.read(16), stream.read(12)
        total = archive.stat().st_size
        payload_bytes = total - len(HEADER) - 16 - 12 - 16
        if payload_bytes <= 0:
            raise ValueError("Truncated archive")
        stream.seek(-16, os.SEEK_END)
        tag = stream.read(16)
        stream.seek(len(HEADER) + 28)
        key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode("utf-8"))
        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
        partial = output.with_suffix(output.suffix + ".partial") if output else None
        owned_partial = False
        try:
            if partial and (partial.exists() or output.exists()):
                raise FileExistsError("Destination already exists")
            target = partial.open("xb") if partial else None
            owned_partial = target is not None
            try:
                remaining = payload_bytes
                while remaining:
                    chunk = stream.read(min(CHUNK, remaining))
                    if not chunk:
                        raise RuntimeError("Truncated ciphertext")
                    clear = decryptor.update(chunk)
                    if target:
                        target.write(clear)
                    remaining -= len(chunk)
                final = decryptor.finalize()  # raises on bad key or altered bytes
                if target:
                    target.write(final)
            finally:
                if target:
                    target.close()
            if partial:
                # Link is atomic and fails if output exists; never replace prior backup.
                os.link(partial, output)
                partial.unlink()
                owned_partial = False
        finally:
            if owned_partial and partial and partial.exists():
                partial.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify or decrypt a protected TALVOA backup.")
    parser.add_argument("archive", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, help="Explicit path for plaintext dump (sensitive)")
    args = parser.parse_args()
    clients = require_clients() if args.output else {}
    if args.output:
        if args.output.parent.is_symlink():
            raise RuntimeError("Output folder symlink is not allowed")
        verify_private_windows_acl(args.output.parent.resolve(strict=True))
        print("WARNING: --output writes SENSITIVE PLAINTEXT customer data.")
        if input("Type DECRYPT to proceed: ") != "DECRYPT":
            raise RuntimeError("Cancelled")
    password = getpass.getpass("Backup passphrase (hidden input): ")
    decrypt_archive(args.archive, password, args.output)
    if args.output:
        with open(os.devnull, "wb") as output:
            check = subprocess.run([clients["pg_restore"], "--list", str(args.output)],
                                   stdout=output, stderr=subprocess.DEVNULL, check=False)
        if check.returncode:
            raise RuntimeError("pg_restore cannot read decrypted archive")
        print("Decrypted PostgreSQL archive validated:", args.output)
        print("Restore ONLY into an isolated disposable test DB; remove plaintext after use.")
    else:
        print("PASS: encrypted archive authentication verified; no plaintext was written.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAILED:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
