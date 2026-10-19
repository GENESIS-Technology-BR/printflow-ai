"""TALVOA homologation: explicit structural migration runner.

Dry-run is the default. Does not run data cleanup or financial seeds.
Run only with the homologation DATABASE_URL and --apply after review.
"""
import argparse
import os
from urllib.parse import urlparse

from backend.app.database.connection import engine, Base
# Explicit model imports register metadata without importing FastAPI application.
from backend.app.database import models as database_models
from backend.modules.auth.model import User
from backend.modules.companies.model import Company
from backend.modules.printers.model import Printer
from backend.app.database.migrations import (
    ensure_printer_columns,
    ensure_printer_company_ip_constraint,
    ensure_company_agent_columns,
    ensure_operational_alert_columns,
    ensure_user_security_columns,
    ensure_partner_company_columns,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Execute structural migrations")
    args = parser.parse_args()

    url = os.getenv("DATABASE_URL", "")
    db_name = urlparse(url).path.lstrip("/").lower()
    if engine.dialect.name != "postgresql" or db_name != "talvoa-supritech-homolog-db":
        raise SystemExit("REFUSED: database must be SupriTech homologation PostgreSQL")
    if args.apply and os.getenv("TALVOA_MIGRATION_TARGET") != "supritech-homolog":
        raise SystemExit("REFUSED: set TALVOA_MIGRATION_TARGET=supritech-homolog for explicit authorization")
    if not args.apply:
        print("DRY RUN ONLY: no database connection or changes performed.")
        print("Planned: create missing tables; ensure columns, username index and company/IP constraint.")
        print("Excluded: serial cleanup and Guerra financial configuration.")
        return

    print("Applying structural changes to SupriTech homologation only.")
    Base.metadata.create_all(bind=engine)
    for fn in (
        ensure_printer_columns,
        ensure_printer_company_ip_constraint,
        ensure_company_agent_columns,
        ensure_operational_alert_columns,
        ensure_user_security_columns,
        ensure_partner_company_columns,
    ):
        print("START", fn.__name__, flush=True)
        fn(engine)
        print("DONE", fn.__name__, flush=True)
    print("COMPLETE: structural migrations applied; data migrations excluded.")


if __name__ == "__main__":
    main()
