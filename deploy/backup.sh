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

# One value of the env file, read in a subshell: the other values (SECRET_KEY, ...) never
# reach this shell, and nothing from the file is exported to the children (PT3-F6).
env_value() {
    (
        set +u
        . "$ENV_FILE" > /dev/null
        printf '%s' "${!1-}"
    )
}
db_url="$(env_value DATABASE_URL)"
media_root="$(env_value PRIVATE_MEDIA_ROOT)"

DB_URL_RE='^postgres(ql)?://([^:/@]+):([^@]+)@([^:/@]+):([0-9]+)/([^/?]+)$'
if [[ ! "$db_url" =~ $DB_URL_RE ]]; then
    echo "backup failed: DATABASE_URL must look like postgres://user:password@host:port/name" >&2
    exit 1
fi
pg_user="${BASH_REMATCH[2]}"
pg_password="${BASH_REMATCH[3]}"
pg_host="${BASH_REMATCH[4]}"
pg_port="${BASH_REMATCH[5]}"
pg_database="${BASH_REMATCH[6]}"
if [[ -z "$media_root" ]]; then
    echo "backup failed: PRIVATE_MEDIA_ROOT is not set in the env file" >&2
    exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
db_file="$BACKUP_DIR/db-$STAMP.sql.gz"
media_file="$BACKUP_DIR/media-$STAMP.tar.gz"
mkdir -p "$BACKUP_DIR"
# Write to *.part and rename only after success; a failed step leaves no partial file (PT3-F6).
trap 'rm -f -- "$db_file.part" "$media_file.part"' EXIT
# The PG* values go to pg_dump only, through the libpq environment, never on the command line
# (PT1-F13); gzip, tar and find do not get them.
PGUSER="$pg_user" PGPASSWORD="$pg_password" PGHOST="$pg_host" PGPORT="$pg_port" \
    PGDATABASE="$pg_database" pg_dump --no-owner --no-privileges | gzip -9 > "$db_file.part"
mv -- "$db_file.part" "$db_file"
tar -czf "$media_file.part" -C "$(dirname "$media_root")" "$(basename "$media_root")"
mv -- "$media_file.part" "$media_file"
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'db-*.sql.gz' -o -name 'media-*.tar.gz' \) -mtime +"$((KEEP_DAYS - 1))" -delete
echo "backup ok: $STAMP"
