#!/usr/bin/env bash
# Daily backup: gzip-compressed pg_dump + tar.gz of PRIVATE_MEDIA_ROOT; keeps KEEP_DAYS days.
set -euo pipefail
umask 077
# Start from / so the script works from any directory (find restores the start directory).
cd /
BACKUP_DIR="${BACKUP_DIR:-/srv/deanery/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
# DEANERY_ENV_FILE overrides the env file path (used by the tests).
ENV_FILE="${DEANERY_ENV_FILE:-/etc/deanery/deanery.env}"
set -a
. "$ENV_FILE"
set +a
# The password goes to pg_dump through the libpq environment, never on the command line (PT1-F13).
DB_URL_RE='^postgres(ql)?://([^:/@]+):([^@]+)@([^:/@]+):([0-9]+)/([^/?]+)$'
if [[ ! "$DATABASE_URL" =~ $DB_URL_RE ]]; then
    echo "backup failed: DATABASE_URL must look like postgres://user:password@host:port/name" >&2
    exit 1
fi
export PGUSER="${BASH_REMATCH[2]}" PGPASSWORD="${BASH_REMATCH[3]}" PGHOST="${BASH_REMATCH[4]}"
export PGPORT="${BASH_REMATCH[5]}" PGDATABASE="${BASH_REMATCH[6]}"
unset DATABASE_URL
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
pg_dump --no-owner --no-privileges | gzip -9 > "$BACKUP_DIR/db-$STAMP.sql.gz"
tar -czf "$BACKUP_DIR/media-$STAMP.tar.gz" -C "$(dirname "$PRIVATE_MEDIA_ROOT")" "$(basename "$PRIVATE_MEDIA_ROOT")"
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'db-*.sql.gz' -o -name 'media-*.tar.gz' \) -mtime +"$((KEEP_DAYS - 1))" -delete
echo "backup ok: $STAMP"
