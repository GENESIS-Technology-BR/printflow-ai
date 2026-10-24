# TALVOA — Cloud backup execution decision (2026-10-23)

## Available cloud resources
- Render workspace: GENESIS Technology (`tea-d9o8jvm1egvs739f8ck0`).
- Render homologation DB: `dpg-db7rsb25b2lc739g0img-a`, PostgreSQL 16, Oregon, Free, expires 2026-11-13.
- Render homologation API: `srv-db7rshgm7kps73cknp30`, Python Free, Oregon, Auto-Deploy off.
- Render gateway: `srv-db8vsrff3r2c73fk39f0`, Node Free, Oregon, Auto-Deploy off.
- Neon homologation: `red-hat-77865204`, PostgreSQL 18, **not restored**.

## Safe execution approach
1. Prefer a **one-time, private backup job** executed within an existing authorized Render runtime (not through a public HTTP endpoint).
2. Check whether Render Shell/SSH is available on the existing Free service. **Do not assume Free offers interactive shell.**
3. If shell is unavailable, check an existing approved private runner or VM. Do not create a paid Render Cron Job.
4. Never add a backup HTTP route to the public API, print DATABASE_URL, upload the dump to GitHub/CI artifacts, or open database access to all IPs.
5. Ensure compatible pg_dump/pg_restore tools and TLS. Produce a dump to private durable storage, SHA-256 checksum, encrypted independent copy.
6. Restore to a disposable isolated PostgreSQL database and verify row counts, schema and application smoke tests before cutover.
7. Do not deploy or change production env vars until a reviewed execution path exists.

## Execution gate
**Prepared, NOT RUN.** Existing GitHub backup script: `ops/backup_supritech_homolog.sh`.
**Blocked on:** an authorized runtime with private access and durable protected backup destination.
**Operator action if needed:** confirm Render shell availability, or provide an approved private runner/VM (without sharing secrets in chat).
