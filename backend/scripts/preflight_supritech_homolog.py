"""Read-only schema preflight for SupriTech homologation.

Run inside an authorized Render environment:
  python -m backend.scripts.preflight_supritech_homolog
Never performs DDL or DML; requires explicit target confirmation.
"""
import os
from sqlalchemy import inspect, text
from backend.app.database.connection import engine


def main():
    database = (engine.url.database or "").lower()
    if engine.dialect.name != "postgresql" or database != "talvoa_supritech_homolog_db":
        raise SystemExit("REFUSED: not the SupriTech homologation PostgreSQL database")
    if os.getenv("TALVOA_MIGRATION_TARGET") != "supritech-homolog":
        raise SystemExit("REFUSED: explicit homologation target confirmation required")
    # Connection is used for metadata inspection only, never writes.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        print("PREFLIGHT: database connection OK")
        for name in ("companies_v2", "printers", "users_v2", "partners", "operational_alerts"):
            if name not in tables:
                print(f"TABLE {name}: MISSING")
                continue
            columns = {item["name"] for item in inspector.get_columns(name)}
            print(f"TABLE {name}: PRESENT ({len(columns)} columns)")
            if name == "printers":
                constraints = inspector.get_unique_constraints(name)
                print("PRINTER UNIQUE CONSTRAINTS:", [(item.get("name"), item.get("column_names")) for item in constraints])
            if name == "users_v2":
                print("USERNAME COLUMN:", "PRESENT" if "username" in columns else "MISSING")
    print("PREFLIGHT COMPLETE: read-only; no migrations applied")


if __name__ == "__main__":
    main()
