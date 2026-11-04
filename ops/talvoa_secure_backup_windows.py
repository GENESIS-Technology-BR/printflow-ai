#!/usr/bin/env python3
"""Create a LOCAL encrypted backup of the SupriTech Render Free PostgreSQL.

Requires Python 3.10+, PostgreSQL client pg_dump/pg_restore and cryptography.
The encrypted archive is NOT an independently stored backup until copied off
this workstation. Never run as part of an untrusted PR or paste secrets in chat.
"""
from __future__ import annotations

import getpass
import hashlib
import os
import pathlib
import secrets
import shutil
import subprocess
import sys
import time
import re
from urllib.parse import unquote, urlsplit

DB_NAME = "talvoa_supritech_homolog_db"
DB_HOST = "dpg-db7rsb25b2lc739g0img-a.oregon-postgres.render.com"
DB_USER = "talvoa_supritech_homolog_db_user"
DB_PORT = 5432
HEADER = b"TLVOBK01"
CHUNK = 1024 * 1024


def parse_source(raw: str) -> dict[str, str]:
    parsed = urlsplit(raw.strip())
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("Connection URL must use postgresql://")
    if parsed.hostname != DB_HOST:
        raise ValueError("Refusing unexpected Render hostname")
    if parsed.port not in (None, DB_PORT):
        raise ValueError("Refusing unexpected PostgreSQL port")
    if unquote(parsed.username or "") != DB_USER:
        raise ValueError("Refusing unexpected PostgreSQL user")
    if unquote(parsed.path.lstrip("/")) != DB_NAME:
        raise ValueError("Refusing to back up an unexpected database")
    if not parsed.username or parsed.password is None:
        raise ValueError("Missing username/password")
    return {
        "PGHOST": parsed.hostname,
        "PGPORT": str(DB_PORT),
        "PGDATABASE": DB_NAME,
        "PGUSER": unquote(parsed.username),
        "PGPASSWORD": unquote(parsed.password),
        "PGSSLMODE": "require",
        "PGCONNECT_TIMEOUT": "20",
    }


def require_clients() -> None:
    for name in ("pg_dump", "pg_restore"):
        if not shutil.which(name):
            raise RuntimeError(f"{name} not found. Install PostgreSQL 16 client tools.")
    for name in ("pg_dump", "pg_restore"):
        result = subprocess.run([name, "--version"], capture_output=True, text=True, check=True)
        if not re.search(r"\bPostgreSQL\) 16(?:\.|\b)", result.stdout):
            raise RuntimeError(f"{name} must be PostgreSQL major version 16")
        print("Client:", name, "PostgreSQL 16")


def encrypt_dump(plain: pathlib.Path, encrypted: pathlib.Path, password: str, *, reserved: bool = False) -> None:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(password.encode("utf-8"))
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    with plain.open("rb") as source, encrypted.open("wb" if reserved else "xb") as target:
        target.write(HEADER + salt + nonce)
        for block in iter(lambda: source.read(CHUNK), b""):
            target.write(encryptor.update(block))
        target.write(encryptor.finalize())
        target.write(encryptor.tag)

    # Read and authenticate the complete archive without writing plaintext.
    data_size = encrypted.stat().st_size - len(HEADER) - 16 - 12 - 16
    if data_size < 1:
        raise RuntimeError("Encrypted archive is unexpectedly empty")
    from cryptography.exceptions import InvalidTag
    with encrypted.open("rb") as source:
        if source.read(len(HEADER)) != HEADER:
            raise RuntimeError("Bad encrypted header")
        stored_salt, stored_nonce = source.read(16), source.read(12)
        if stored_salt != salt or stored_nonce != nonce:
            raise RuntimeError("Bad encrypted metadata")
        source.seek(-16, os.SEEK_END)
        tag = source.read(16)
        source.seek(len(HEADER) + 16 + 12)
        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
        remaining = data_size
        while remaining:
            block = source.read(min(CHUNK, remaining))
            if not block:
                raise RuntimeError("Truncated encrypted archive")
            decryptor.update(block)
            remaining -= len(block)
        try:
            decryptor.finalize()
        except InvalidTag as exc:
            raise RuntimeError("Encrypted archive authentication FAILED") from exc


def main() -> None:
    require_clients()
    try:
        import cryptography  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Install 'cryptography' in a trusted Python environment") from exc

    print("Secure backup of SupriTech homologation ONLY. Never paste secrets into chat.")
    raw = getpass.getpass("Render external DATABASE URL (hidden input): ")
    envvars = parse_source(raw)
    raw = ""  # Do not retain the complete URL for later use.
    password = getpass.getpass("New backup encryption PASSPHRASE (20+ chars): ")
    if len(password) < 20:
        raise ValueError("Encryption passphrase must contain at least 20 characters")
    if password != getpass.getpass("Confirm encryption passphrase: "):
        raise ValueError("Passphrases differ")

    outdir = pathlib.Path.home() / "TALVOA_Backups"
    outdir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + secrets.token_hex(8)
    plain = outdir / f".supritech-{stamp}.dump.partial"
    encrypted = outdir / f"supritech-{stamp}.dump.aesgcm"
    partial = outdir / f".supritech-{stamp}.aesgcm.partial"
    env = {**os.environ, **envvars}
    owned_plain = False
    owned_partial = False
    try:
        print("Running pg_dump with TLS; source database is read-only for this operation...")
        with plain.open("xb") as output:
            owned_plain = True
            job = subprocess.run(
                ["pg_dump", "--format=custom", "--no-owner", "--no-acl"],
                stdout=output,
                stderr=subprocess.DEVNULL,
                env=env,
                timeout=900,
                check=False,
            )
        if job.returncode != 0 or plain.stat().st_size == 0:
            raise RuntimeError("pg_dump failed; check database access and PostgreSQL client version")
        with open(os.devnull, "wb") as sink:
            check = subprocess.run(["pg_restore", "--list", str(plain)],
                                   stdout=sink, stderr=subprocess.DEVNULL, check=False)
        if check.returncode:
            raise RuntimeError("pg_restore archive-list validation failed")
        partial.touch(exist_ok=False)  # Reserve a unique file; refuse any collision.
        owned_partial = True
        encrypt_dump(plain, partial, password, reserved=True)
        # Atomic create-if-absent on the same volume: refuse overwrites (no os.replace).
        os.link(partial, encrypted)
        partial.unlink()
        owned_partial = False
        with encrypted.open("rb") as stream:
            digest_hasher = hashlib.sha256()
            for block in iter(lambda: stream.read(CHUNK), b""):
                digest_hasher.update(block)
            digest = digest_hasher.hexdigest()
        print("ENCRYPTED BACKUP READY:", encrypted)
        print("Encrypted archive SHA256:", digest)
        print("IMPORTANT: copy .aesgcm file to protected independent cloud storage.")
        print("IMPORTANT: an isolated test RESTORE is still required before declaring success.")
    finally:
        envvars["PGPASSWORD"] = ""
        env["PGPASSWORD"] = ""
        password = ""
        if owned_plain:
            plain.unlink(missing_ok=True)
        if owned_partial:
            partial.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("BACKUP NOT VERIFIED:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
