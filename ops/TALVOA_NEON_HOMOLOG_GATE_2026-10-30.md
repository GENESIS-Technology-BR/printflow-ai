# TALVOA — Neon homologation gate — 2026-10-30

## Verified live
- Neon project `red-hat-77865204` (`talvoa-supritech-homolog`) exists; PostgreSQL 18.
- Default branch id `br-green-meadow-b5bfvn7e`, branch name `production` **within the homologation project**. This label does NOT mean TALVOA production.
- Read-only SQL on `neondb`: **0 public base tables**. Destination remains un-restored.
- Separate real production project: `proud-union-87295556` — do not modify.
- Render source `dpg-db7rsb25b2lc739g0img-a` PG16 available; recorded expiry 2026-11-13T17:38:52Z.
- Render database external access from hosted connector failed due to SSL/TLS and allowlist restrictions; do not broaden ingress.

## Existing migration code review
- `backend/scripts/talvoa_supritech_migration_runner.py`: dry-run default, source and destination identity checks, host pin, version check, target object count check, local restricted file creation, recovery verification flags.
- `backend/scripts/talvoa_supritech_verify_restore.py`: compares tables and exact row counts.
- `ops/backup_supritech_homolog.sh`: local dump + archive list + checksum, not a restore test.
- Existing migration script must NEVER be run with `--apply` until an independent, successfully restored backup is proven and a trusted source-network execution environment exists.

## Operational blockers
1. Source-side authorized execution host with TLS and network access.
2. Private durable location for encrypted backup.
3. Real test restore against disposable isolated database; verified row counts and permissions.
4. Only after validation, migration cutover approval and API connection configuration.

## Safe next actions
- Determine whether the authorized Windows operator can connect privately; no credentials in chat, CI logs, or public HTTP routes.
- Validate client pg_dump major >= 16, destination in project `red-hat-77865204` (not merely a URL with `.neon.tech`).
- Preserve production and existing branch; no automatic API cutover.
