"""Read-only TALVOA migration inventory; never prints secrets."""
import argparse
import json
import os
import subprocess
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("migration", Path(__file__).with_name("talvoa_supritech_migration_runner.py"))
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)

SQL = """
SELECT json_build_object(
  'database', current_database(),
  'tables', (SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'),
  'sequences', (SELECT count(*) FROM information_schema.sequences WHERE sequence_schema='public'),
  'constraints', (SELECT count(*) FROM information_schema.table_constraints WHERE table_schema='public'),
  'relations', COALESCE((SELECT json_agg(json_build_object('table', relname, 'rows_estimate', GREATEST(reltuples::bigint,0)) ORDER BY relname)
   FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname='public' AND c.relkind IN ('r','p')), '[]'::json)
)::text;
"""

def inventory(url):
    proc = subprocess.run(["psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-c", SQL],
                          env=migration.pg_env(url), capture_output=True, text=True, check=True, timeout=90)
    return json.loads(proc.stdout.strip())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="store_true")
    parser.add_argument("--target", action="store_true")
    args = parser.parse_args()
    if args.source == args.target:
        raise SystemExit("Specify exactly one of --source or --target")
    source = os.environ.get("TALVOA_SOURCE_DATABASE_URL", "")
    target = os.environ.get("TALVOA_TARGET_DATABASE_URL", "")
    if not source or not target:
        raise SystemExit("Missing migration secrets")
    migration.verify(source, target)
    expected_host = os.environ.get("TALVOA_EXPECTED_NEON_HOST", "").strip().lower()
    if not expected_host or migration.database(target)[1] != expected_host:
        raise SystemExit("REFUSED: target hostname must match TALVOA_EXPECTED_NEON_HOST")
    data = inventory(source if args.source else target)
    print(json.dumps({"role": "source" if args.source else "target", "inventory": data}, indent=2))

if __name__ == "__main__":
    main()
