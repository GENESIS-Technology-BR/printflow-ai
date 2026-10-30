# TALVOA — SupriTech database migration runbook

**Scope:** SupriTech staging only. Production/Guerra are out of scope.
**Current source:** Render PostgreSQL `talvoa_supritech_homolog_db` (Render ID `dpg-db7rsb25b2lc739g0img-a`).
**Target:** isolated Neon project `red-hat-77865204`, database `neondb`.
**Cutover:** never automatic. Requires separate verification of application behavior and rollback readiness.

## Prerequisites
1. Confirm Render database remains available and has a recoverable backup.
2. Verify Neon target is isolated, empty and reachable with SSL; confirm hostname against the intended Neon project (the runner currently validates provider suffix, not the exact project).
3. Configure secrets in a trusted, isolated execution environment. Do not paste connection strings in logs or commit them.
4. Restrict source access to the trusted executor; do not widen the IP allowlist to 0.0.0.0/0.
5. Avoid concurrent writes while taking the final migration snapshot; schedule a maintenance window or a verified replication strategy.

## Execution gates
- **Gate 0:** offline tests: `python -m unittest discover -s backend/tests -p 'test_supritech_*.py' -v`.
- **Gate 1:** source and target read-only inventory with `talvoa_supritech_inventory.py --source` and `--target`.
- **Gate 2:** export and retain an encrypted backup outside the ephemeral runner; verify backup file exists, is nonzero and can be restored into a disposable test database.
- **Gate 3:** only with explicit staging approval and verified empty target, run `talvoa_supritech_migration_runner.py --apply`.
- **Gate 4:** compare exact table counts with `talvoa_supritech_verify_restore.py`. This is necessary but insufficient: validate constraints, sequences, login, tenant isolation, printer agent ingestion, reporting and data freshness.
- **Gate 5:** cut over only the SupriTech homolog API `DATABASE_URL`; never touch production secrets. Monitor errors and ingestion.
- **Gate 6:** rollback by restoring the previous API connection value *only if write consistency and data reconciliation are understood*. Otherwise stop writes and investigate before switching back.

## Known constraints
- Render-hosted database's IP allowlist currently prevents hosted connector SQL access.
- Render Free PostgreSQL reports expiry on 2026-11-13.
- The GitHub Actions preflight is offline; it does not perform dump/restore.
- The migration runner is a guarded prototype, not yet an end-to-end approved unattended executor.
- Neon Free has usage and availability limits; monitor quota and keep independent backups.
