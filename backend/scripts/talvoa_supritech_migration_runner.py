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
from urllib.parse import urlsplit, parse_qs, unquote

SOURCE_DB = "talvoa_supritech_homolog_db"
SOURCE_HOST_PREFIX = "dpg-db7rsb25b2lc739g0img-a"
TARGET_DB = "neondb"


def database(url):
    parsed = urlsplit(url)
    return parsed.path.lstrip("/"), (parsed.hostname or "").lower(), parsed


def verify(source, target):
    sdb, shost, _ = database(source)
    tdb, thost, parsed = database(target)
    if sdb != SOURCE_DB or shost not in (SOURCE_HOST_PREFIX, SOURCE_HOST_PREFIX + '.oregon-postgres.render.com'):
        raise ValueError("Source is not the approved SupriTech Render database")
    if tdb != TARGET_DB or (not thost.endswith(".neon.tech") or not thost.startswith("ep-")):
        raise ValueError("Target must be the dedicated SupriTech Neon neondb")
    if shost == thost:
        raise ValueError("Source and target must differ")
    if parse_qs(parsed.query).get("sslmode", [""])[0] not in ("require", "verify-full", "verify-ca"):
        raise ValueError("Target must specify sslmode=require or stronger")


def pg_env(url):
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    env = os.environ.copy()
    env.update({
        'PGHOST': parsed.hostname or '',
        'PGPORT': str(parsed.port or 5432),
        'PGDATABASE': unquote(parsed.path.lstrip('/')),
        'PGUSER': unquote(parsed.username or ''),
        'PGPASSWORD': unquote(parsed.password or ''),
        'PGSSLMODE': query.get('sslmode', ['require'])[0],
    })
    return env


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
    expected_host = os.environ.get("TALVOA_EXPECTED_NEON_HOST", "").lower().strip()
    if not expected_host or database(target)[1] != expected_host:
        raise SystemExit("REFUSED: target hostname must match TALVOA_EXPECTED_NEON_HOST")
    for binary in ("pg_dump", "pg_restore", "psql"):
        if not shutil.which(binary):
            raise SystemExit(f"REFUSED: {binary} not installed")
    # Fail closed: never restore into a nonempty database.
    result = subprocess.run(
        ["psql", "-X", "-A", "-t", "-c",
         "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','v','m','S','f')"],
        capture_output=True, text=True, timeout=60, check=True, env=pg_env(target),
    )
    if result.stdout.strip() != "0":
        raise SystemExit("REFUSED: destination contains database objects")
    backup = Path(args.backup)
    if not backup.parent.is_dir():
        raise SystemExit("REFUSED: backup directory does not exist")
    if backup.is_symlink():
        raise SystemExit("REFUSED: backup path must not be a symbolic link")
    if backup.exists():
        raise SystemExit("REFUSED: backup path already exists")
    try:
        # Restrict backup permissions before writing any database content.
        fd = os.open(str(backup), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as output:
            run(["pg_dump", "--format=custom", "--no-owner", "--no-acl"],
                env=pg_env(source), stdout=output)
        if backup.stat().st_size == 0:
            raise SystemExit("REFUSED: empty backup; restore cancelled")
        run(["pg_restore", "--list", str(backup)], env=os.environ.copy(), stdout=subprocess.DEVNULL)
        print("Backup created and archive index verified. Keep it encrypted and restrict access.")
        if os.environ.get("TALVOA_BACKUP_VERIFIED") != "supritech-homolog":
            raise SystemExit("REFUSED: backup recovery verification not acknowledged; restore cancelled")
        run(["pg_restore", "--exit-on-error", "--no-owner", "--no-acl",
             str(backup)], env=pg_env(target))
        print("RESTORE FINISHED. Validation and API cutover are separate manual gates.")
    except Exception:
        print("FAILED: target may be partially restored. Do not cut over.", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
