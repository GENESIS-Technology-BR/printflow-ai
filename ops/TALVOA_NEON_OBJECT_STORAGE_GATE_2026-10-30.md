# TALVOA — Cloud backup storage discovery (2026-10-30)

## Verified on Neon
- Project: talvoa-supritech-homolog (red-hat-77865204)
- Branch: br-green-meadow-b5bfvn7e
- Branchable object storage: enabled (read-only capability check).
- Buckets: none.
- No bucket created; no file uploaded; no backup performed.

## Verified in CI
- Render Free Wake Audit successful for commit 833802d.
- PostgreSQL Backup Safety offline workflow successful for commit 833802d.
- These jobs perform static validation only and do not extract customer data.

## Required gates before migration
1. Confirm object storage free-tier quota, encryption, data retention and download compatibility.
2. Confirm Render PG16 source network access with least-privileged temporary IP allowlist, no 0.0.0.0/0.
3. Validate a one-time executor with protected secrets, pg_dump version >=16, TLS, and encrypted independent durable backup.
4. Restore to a disposable isolated database and compare contents.
5. Only then evaluate cutover into Neon homologation; leave production intact.

## Status
Storage path discovered, but migration is blocked by source network access and unverified persistent backup. No live environment mutated.
