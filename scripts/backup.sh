#!/bin/sh
set -eu

TS="$(date +%Y%m%d_%H%M%S)"
OUT="/backups/finance_db_${TS}.sql.gz"

: "${PGPASSWORD:?PGPASSWORD is required}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-finance_user}"
DB_NAME="${DB_NAME:-finance_db}"

mkdir -p /backups

pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "$OUT"

echo "Backup written to $OUT"
