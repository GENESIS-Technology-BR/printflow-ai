#!/usr/bin/env python3
"""TALVOA SupriTech PostgreSQL migration runner. Dry-run by default.

Requires pg_dump, pg_restore, psql and two environment secrets:
TALVOA_SOURCE_DATABASE_URL and TALVOA_TARGET_DATABASE_URL.
Never prints connection strings. Run from an isolated trusted runner.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

SOURCE_DB = "talvoa_supritech_homolog_db"
SOURCE_HOST_PREFIX = "dpg-db7rsb25b2lc739g0img-a"
TARGET_DB = "neondb"


def database(url):
    parsed = urlsplit(url)
    return parsed.path.lstrip("/"), (parsed.hostname or "").lower(), parsed


def verify(source, target):
    sdb, shost, _ = database(source)
    tdb, thost, parsed = database(target)
    if sdb != SOURCE_DB or not shost.startswith(SOURCE_HOST_PREFIX):
        raise ValueError("Source is not the approved SupriTech Render database")
    if tdb != TARGET_DB or not thost.endswith(".neon.tech"):
        raise ValueError("Target must be the dedicated SupriTech Neon neondb")
    if shost == thost:
        raise ValueError("Source and target must differ")
    if parse_qs(parsed.query).get("sslmode", [""])[0] not in ("require", "verify-full", "verify-ca"):
        raise ValueError("Target must specify sslmode=require or stronger")


def run(cmd, *, env, stdout=None):
    subprocess.run(cmd, check=True, env=env, stdout=stdout, timeout=1800)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Perform backup and restore; default is dry-run")
    parser.add_argument("--backup", default="supritech-homolog.dump")
    args = parser.parse_args()
    source = os.environ.get("TALVOA_SOURCE_DATABASE_URL", "")
    target = os.environ.get("TALVOA_TARGET_DATABASE_URL", "")
    if not source or not target:
        raise SystemExit("Missing source or target database secret; no changes made")
    try:
        verify(source, target)
    except ValueError as exc:
        raise SystemExit(f"REFUSED: {exc}") from None
    print("Approved SupriTech source and Neon destination identifiers verified.")
    print("Plan: dump source, restore into empty target, then validate separately.")
    if not args.apply:
        print("DRY RUN: no connections or database changes.")
        return
    if os.environ.get("TALVOA_MIGRATION_APPROVED") != "supritech-homolog":
        raise SystemExit("REFUSED: TALVOA_MIGRATION_APPROVED must be supritech-homolog")
    for binary in ("pg_dump", "pg_restore", "psql"):
        if not shutil.which(binary):
            raise SystemExit(f"REFUSED: {binary} not installed")
    # Fail closed: never restore into a nonempty database.
    result = subprocess.run(
        ["psql", target, "-X", "-A", "-t", "-c",
         "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"],
        capture_output=True, text=True, timeout=60, check=True,
    )
    if result.stdout.strip() != "0":
        raise SystemExit("REFUSED: destination already has public tables")
    backup = Path(args.backup)
    if backup.exists():
        raise SystemExit("REFUSED: backup path already exists")
    try:
        with backup.open("xb") as output:
            run(["pg_dump", "--format=custom", "--no-owner", "--no-acl", "--dbname", source],
                env=os.environ.copy(), stdout=output)
        print("Backup created. Keep it encrypted and restrict access.")
        run(["pg_restore", "--exit-on-error", "--no-owner", "--no-acl",
             "--dbname", target, str(backup)], env=os.environ.copy())
        print("RESTORE FINISHED. Validation and API cutover are separate manual gates.")
    except Exception:
        print("FAILED: target may be partially restored. Do not cut over.", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
