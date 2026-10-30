#!/usr/bin/env bash
# TALVOA SupriTech: preflight only, no database writes or backup exports.
set -Eeuo pipefail
umask 077
: "${DATABASE_URL:?Set DATABASE_URL privately; do not paste it into chat}"
command -v psql >/dev/null || { echo "ERROR: psql not installed"; exit 1; }
command -v pg_dump >/dev/null || { echo "ERROR: pg_dump not installed"; exit 1; }
command -v pg_restore >/dev/null || { echo "ERROR: pg_restore not installed"; exit 1; }

echo "Checking PostgreSQL client tools..."
psql --version
pg_dump --version
pg_restore --version

echo "Checking TLS connection and source identity (read-only)..."
# No credentials or URL are printed; psql uses the environment.
PGSSLMODE=verify-full psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -Atqc \
  "SELECT current_database(), current_setting('server_version'), current_setting('ssl');" \
  || { echo "TLS verified connection failed; check CA, network allowlist and DB credentials"; exit 1; }

echo "Preflight complete. No backup was created."
