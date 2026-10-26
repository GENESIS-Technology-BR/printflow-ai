# SupriTech homologation — Render private PostgreSQL connectivity

## Verified topology
- Source: Render Postgres `dpg-db7rsb25b2lc739g0img-a`, Oregon, PostgreSQL 16.
- Executor candidate: Render web service `srv-db7rshgm7kps73cknp30`, Oregon, same workspace.
- Destination: dedicated Neon project `red-hat-77865204`, database `neondb`. Never use the production Neon project.

## Root cause
The hosted Render MCP PostgreSQL query uses the external database endpoint and has no stable outbound IP to allowlist. The source database restricts external IPs and requires TLS. Do not add `0.0.0.0/0`.

## Safe remediation
1. In Render Dashboard > source Postgres > Connect, obtain the **Internal** URL. Never commit it, print it in logs, or send it in chat.
2. Use an ephemeral, authenticated execution context in the **same Render workspace and Oregon region**. Prefer a one-off controlled task rather than exposing a public migration endpoint. Confirm the environment can execute `psql`, `pg_dump`, and `pg_restore`.
3. Inject the internal source URL as `TALVOA_SOURCE_DATABASE_URL` and the dedicated Neon destination URL as `TALVOA_TARGET_DATABASE_URL` via protected runtime secrets. For the internal Render URL, require TLS with `sslmode=require` if supported by the client configuration. For Neon require TLS and exact destination hostname.
4. Execute **read-only inventory first**. Confirm source schema and destination emptiness, compare PostgreSQL versions, and verify the Neon role has sufficient privileges.
5. Export source to a private encrypted backup location with restrictive permissions. Verify archive integrity and perform an isolated **test restore**, not merely an acknowledgment flag. Retain a rollback copy.
6. Freeze writes or establish a consistent delta-sync plan. Obtain an explicit maintenance window before final export.
7. Only after recovery verification, run the guarded staging restore and compare table counts, constraints, sequences, and critical application queries. Keep the existing Render database and API connection unchanged until acceptance.
8. Do not merge PR #69, change production, or expose credentials.

## Important compatibility gate
Source PostgreSQL 16 and Neon PostgreSQL 18 differ in major version. Use a compatible `pg_dump` client (16 or newer, ideally 18), test restoration into Neon 18, and resolve extension/collation incompatibilities before cutover.

## Current execution status
Network architecture confirmed; actual private-network SQL access, backup, recovery test, and data migration **not yet executed**. The hosted Render MCP cannot bypass the external IP restriction.
