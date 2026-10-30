#!/usr/bin/env bash
# Manual, local backup for the dedicated SupriTech homologation PostgreSQL.
# Run only on an authorized machine with pg_dump, pg_restore and access to the DB.
# The backup contains customer data: NEVER commit it or upload to CI artifacts.
set -Eeuo pipefail
umask 077

: "${DATABASE_URL:?Set DATABASE_URL privately (do not paste it into chat or logs)}"
: "${BACKUP_DIR:?Set BACKUP_DIR to a protected directory outside the repository}"
command -v pg_dump >/dev/null || { echo "pg_dump is required" >&2; exit 1; }
command -v pg_restore >/dev/null || { echo "pg_restore is required" >&2; exit 1; }
command -v sha256sum >/dev/null || { echo "sha256sum is required" >&2; exit 1; }

mkdir -p -- "$BACKUP_DIR"
chmod 700 -- "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="$BACKUP_DIR/talvoa-supritech-homolog-$timestamp.dump"
trap 'if [[ -n "${temporary:-}" && -f "$temporary" ]]; then rm -f -- "$temporary"; fi' EXIT
temporary="$destination.partial"
echo "Creating encrypted-transport PostgreSQL custom-format backup (local file)."
# pg_dump reads DATABASE_URL from the environment, not command-line arguments.
PGSSLMODE=require pg_dump --dbname="$DATABASE_URL" --format=custom --no-owner --no-acl --file="$temporary"
pg_restore --list "$temporary" >/dev/null
mv -- "$temporary" "$destination"
temporary=""
sha256sum "$destination" > "$destination.sha256"
echo "Backup created and archive catalog verified: $destination"
echo "SHA-256 saved to: $destination.sha256"
echo "IMPORTANT: pg_restore --list only verifies archive readability, NOT a successful database restore."
echo "Next: restore to an isolated disposable PostgreSQL instance and validate application data."
