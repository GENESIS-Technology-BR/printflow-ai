# TALVOA — SupriTech homologation preservation gate

**Scope:** Render PostgreSQL `talvoa-supritech-homolog-db` (`dpg-db7rsb25b2lc739g0img-a`).
**Deadline:** 2026-11-13 (free database expiration).
**Policy:** No production changes, database writes, credential rotations, public database exposure, or migration without separate approval.

## Current state
- Read-only inventory: `ops/audit_supritech_accounts.py` (not yet run against Render).
- Manual backup: `ops/backup_supritech_homolog.sh` (not yet run).
- GitHub workflow: `.github/workflows/supritech-readonly-audit.yml` requires a dedicated `talvoa-db-audit` self-hosted runner, which has **not** been provisioned.
- A temporary external PostgreSQL inbound IP rule remains to be removed after a verified alternative access path exists.

## Gate A — Authorized execution environment
1. Select an Always Free cloud VM only after checking account eligibility, available capacity, architecture, and billing guardrails.
2. Restrict SSH access; keep OS patched; no inbound PostgreSQL port.
3. Install PostgreSQL client tools of compatible major version and Docker only if needed.
4. Configure network access from the VM to the Render database using a narrowly scoped source IP. Do **not** allow `0.0.0.0/0`.
5. Provision a **read-only database role** for audits where feasible, and a separate minimally privileged backup role. Creation of roles requires explicit authorization.
6. Store secrets only in the protected runtime secret store. Never put connection URLs in repository, screenshots, shell history or logs.

## Gate B — First backup (mandatory before migration)
1. Verify the database identity and expected tables; record a non-sensitive inventory.
2. Run `ops/backup_supritech_homolog.sh` on the authorized host with protected `DATABASE_URL` and `BACKUP_DIR` environment variables.
3. Keep resulting dump and checksum outside the Git repository and GitHub Actions artifacts.
4. Encrypt backup at rest, store a second copy independently of the VM and Render, and document retention/access controls.
5. Verify checksum and **restore into a disposable isolated PostgreSQL database**; validate schema, key row counts and application smoke tests.
6. Record date, dump size, checksum, restore outcome, and operator. Only a successful restore counts as a verified backup.

## Gate C — Migration readiness
1. Inventory extensions, database size, schema versions, roles, connections, and app `DATABASE_URL` dependencies.
2. Check target free-tier storage/compute limits and region; verify portability of extensions and migrations.
3. Rehearse restore to target in isolation and compare data.
4. Plan a short write-free cutover window and a rollback path; never switch application secrets before approval.
5. Keep Render database until the target is verified and rollback requirements are met.

## Gate D — SupriTech functional validation
1. Confirm partner and user membership using the read-only audit.
2. Validate TALVOA platform-admin versus partner-admin access using dedicated test accounts.
3. Verify tenant isolation with negative tests (no cross-tenant records).
4. Demonstrate Agent → API → database → portal → reports, including printer counters and alerts.
5. Document results and blockers; only then declare customer-ready.

## Stop conditions
- No authorized access path or insufficient backup permissions.
- Backup not produced or restore not verified.
- Credentials appear in logs or external access rules are too broad.
- Target free tier lacks capacity or an expiry condition threatens data retention.

## Immediate operator checklist
- [ ] Provision dedicated VM and controlled network access
- [ ] Configure protected credentials (separate audit and backup permissions)
- [ ] Produce first dump
- [ ] Restore and validate independently
- [ ] Remove temporary inbound rule `201.72.238.194/32` once no longer needed
- [ ] Prepare migration plan and obtain approval
