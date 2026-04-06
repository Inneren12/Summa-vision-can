#!/usr/bin/env bash
# ============================================================================
# Summa Vision — PostgreSQL Backup Script
#
# Dumps the database, compresses it, uploads to S3, and cleans up old backups.
#
# Required env vars:
#   DATABASE_URL    — PostgreSQL connection string
#   BACKUP_S3_BUCKET — S3 bucket for backups (e.g. summa-vision-backups)
#
# Optional env vars:
#   BACKUP_RETENTION_DAYS — Delete backups older than N days (default: 30)
#   AWS_DEFAULT_REGION    — AWS region (default: us-east-1)
#   S3_ENDPOINT_URL       — Custom S3 endpoint (for MinIO in dev)
#
# S3 key pattern: backups/{yyyy-mm-dd}/summa_{timestamp}.sql.gz
#
# Usage:
#   # Manual run:
#   ./scripts/ops/backup_db.sh
#
#   # Cron (nightly 3am):
#   0 3 * * * /app/scripts/ops/backup_db.sh >> /var/log/backup.log 2>&1
# ============================================================================

set -euo pipefail

# --- Configuration ---
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
DATE="$(date +%Y-%m-%d)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DUMP_FILE="/tmp/summa_${TIMESTAMP}.sql.gz"
S3_KEY="backups/${DATE}/summa_${TIMESTAMP}.sql.gz"

# --- Validate required vars ---
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL is not set" >&2
    exit 1
fi

if [ -z "${BACKUP_S3_BUCKET:-}" ]; then
    echo "ERROR: BACKUP_S3_BUCKET is not set" >&2
    exit 1
fi

# --- Extract connection details from DATABASE_URL ---
# Format: postgresql+asyncpg://user:pass@host:port/dbname
# Strip the driver prefix for pg_dump
PG_URL=$(echo "${DATABASE_URL}" | sed 's|postgresql+asyncpg://|postgresql://|')

echo "[$(date -Iseconds)] Starting backup..."

# --- Dump and compress ---
pg_dump "${PG_URL}" | gzip > "${DUMP_FILE}"
DUMP_SIZE=$(du -h "${DUMP_FILE}" | cut -f1)
echo "[$(date -Iseconds)] Dump created: ${DUMP_FILE} (${DUMP_SIZE})"

# --- Upload to S3 ---
S3_ARGS=""
if [ -n "${S3_ENDPOINT_URL:-}" ]; then
    S3_ARGS="--endpoint-url ${S3_ENDPOINT_URL}"
fi

aws s3 cp "${DUMP_FILE}" "s3://${BACKUP_S3_BUCKET}/${S3_KEY}" ${S3_ARGS}
echo "[$(date -Iseconds)] Uploaded to s3://${BACKUP_S3_BUCKET}/${S3_KEY}"

# --- Cleanup local dump ---
rm -f "${DUMP_FILE}"

# --- Delete old backups from S3 ---
if [ "${RETENTION_DAYS}" -gt 0 ]; then
    CUTOFF_DATE=$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%d 2>/dev/null \
        || date -v-${RETENTION_DAYS}d +%Y-%m-%d)  # macOS fallback

    echo "[$(date -Iseconds)] Cleaning backups older than ${RETENTION_DAYS} days (before ${CUTOFF_DATE})..."

    aws s3 ls "s3://${BACKUP_S3_BUCKET}/backups/" ${S3_ARGS} \
        | awk '{print $NF}' \
        | sed 's|/$||' \
        | while read -r dir; do
            if [[ "${dir}" < "${CUTOFF_DATE}" ]]; then
                echo "  Deleting backups/${dir}/"
                aws s3 rm "s3://${BACKUP_S3_BUCKET}/backups/${dir}/" \
                    --recursive ${S3_ARGS} --quiet
            fi
        done
fi

echo "[$(date -Iseconds)] Backup complete."