#!/usr/bin/env python3
"""Read-only SupriTech account inventory. Run inside the homologation private network.

Usage: DATABASE_URL=... python ops/audit_supritech_accounts.py
Requires psycopg2-binary (already in requirements.txt).
Never prints credentials, password hashes, tokens, or full email addresses.
"""
import os
import sys
import psycopg2
from psycopg2 import sql

def mask_email(value):
    if not value or "@" not in str(value):
        return "(not set)"
    local, domain = str(value).split("@", 1)
    return (local[:2] + "***@" + domain)

def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not configured", file=sys.stderr)
        return 2
    conn = psycopg2.connect(url, connect_timeout=10)
    try:
        conn.set_session(readonly=True, autocommit=False)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                  AND table_type = 'BASE TABLE'
                  AND (table_name ILIKE '%partner%' OR table_name ILIKE '%user%' OR table_name ILIKE '%compan%')
                ORDER BY table_schema, table_name
            """)
            tables = cur.fetchall()
            print("Relevant tables:", len(tables))
            for schema, table in tables:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema=%s AND table_name=%s
                """, (schema, table))
                columns = {row[0] for row in cur.fetchall()}
                print(f"- {schema}.{table}: columns=" + ",".join(sorted(
                    c for c in columns if c in {"id", "name", "email", "role", "active", "partner_id", "user_id", "company_id"}
                )))
                identity = [c for c in ("name", "email") if c in columns]
                if not identity:
                    continue
                select_cols = [c for c in ("id", "name", "email", "role", "active", "partner_id", "user_id", "company_id") if c in columns]
                predicate = sql.SQL(" OR ").join(
                    sql.SQL("{} ILIKE %s").format(sql.Identifier(c)) for c in identity
                )
                query = sql.SQL("SELECT {} FROM {}.{} WHERE {} LIMIT 25").format(
                    sql.SQL(", ").join(map(sql.Identifier, select_cols)),
                    sql.Identifier(schema), sql.Identifier(table), predicate
                )
                cur.execute(query, tuple("%supri%" for _ in identity))
                records = cur.fetchall()
                print("  SupriTech matches:", len(records))
                for record in records:
                    safe = dict(zip(select_cols, record))
                    if "email" in safe:
                        safe["email"] = mask_email(safe["email"])
                    print("  ", safe)
            print("NOTE: A matching partner name alone does not prove an active partner-admin account.")
            print("Confirm user-to-partner membership and test API authorization before customer access.")
        conn.rollback()
    finally:
        conn.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
