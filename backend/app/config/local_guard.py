"""Fail-closed configuration guard for TALVOA's disposable local work database.

No external dependencies. This protects historical snapshots against startup
schema changes and prevents remote databases being used in local homologation.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

LOCAL_ENVIRONMENT = "local_homologation"
LOCAL_PORT = 60440
LOCAL_DATABASE_PREFIX = "talvoa_local_work_"


def validate_local_database_url(url: str) -> None:
    """Reject anything except a dedicated loopback PostgreSQL work database."""
    if not url or any(ch.isspace() for ch in url):
        raise RuntimeError("Local homologation requires a private DATABASE_URL")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("Invalid local PostgreSQL URL") from exc
    if parsed.scheme not in {"postgresql", "postgresql+psycopg2"}:
        raise RuntimeError("Local homologation requires PostgreSQL, never SQLite")
    if parsed.hostname not in {"127.0.0.1", "localhost"} or port != LOCAL_PORT:
        raise RuntimeError("Local homologation requires loopback PostgreSQL port 60440")
    if parsed.query or parsed.fragment:
        raise RuntimeError("Local homologation rejects URL query/fragment overrides")
    database = parsed.path.removeprefix("/")
    if not re.fullmatch(r"talvoa_local_work_[a-z0-9_]+", database):
        raise RuntimeError("Local homologation requires a dedicated talvoa_local_work_* database")
    if not parsed.username or not parsed.password or "/" in database:
        raise RuntimeError("Local homologation requires an explicit database login")


def should_run_startup_migrations(environment: str, database: str) -> bool:
    """Historical behavior remains unchanged outside explicit local mode."""
    if environment.strip().lower() == LOCAL_ENVIRONMENT:
        return False
    return database.strip().lower() != "talvoa_supritech_homolog_db"
