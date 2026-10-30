"""Read-only post-restore comparison of SupriTech database structure and row counts."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path

spec = importlib.util.spec_from_file_location("migration", Path(__file__).with_name("talvoa_supritech_migration_runner.py"))
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)

TABLES_SQL = """SELECT COALESCE(json_agg(table_name ORDER BY table_name),'[]'::json)::text
FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"""

def sql(url, statement):
    result = subprocess.run(["psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-c", statement],
                            env=migration.pg_env(url), capture_output=True, text=True, check=True, timeout=120)
    return result.stdout.strip()

def quote_ident(name):
    return '"' + name.replace('"', '""') + '"'

def snapshot(url):
    tables = json.loads(sql(url, TABLES_SQL))
    return {name: int(sql(url, "SELECT count(*) FROM public." + quote_ident(name) + ";")) for name in tables}

def main():
    source = os.getenv("TALVOA_SOURCE_DATABASE_URL", "")
    target = os.getenv("TALVOA_TARGET_DATABASE_URL", "")
    if not source or not target:
        raise SystemExit("Missing migration secrets")
    migration.verify(source, target)
    a = snapshot(source)
    b = snapshot(target)
    missing = sorted(set(a) - set(b))
    extra = sorted(set(b) - set(a))
    mismatch = {k: {"source": a[k], "target": b[k]} for k in sorted(set(a) & set(b)) if a[k] != b[k]}
    report = {"source_tables": len(a), "target_tables": len(b), "missing": missing, "extra": extra, "row_count_mismatches": mismatch}
    print(json.dumps(report, indent=2))
    if missing or extra or mismatch:
        raise SystemExit("FAIL: schema or row counts differ; cutover forbidden")
    print("PASS: table names and exact row counts match; application-level validation still required.")

if __name__ == "__main__":
    main()
