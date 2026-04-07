#!/usr/bin/env bash
# ============================================================================
# Summa Vision — PostgreSQL Backup Script
#
# Dumps the database, compresses it, and uploads to S3.
#
# Required env vars:
#   DATABASE_URL       — PostgreSQL connection string
#   BACKUP_S3_BUCKET   — S3 bucket for backups
#
# Optional env vars:
#   S3_ENDPOINT_URL    — Custom S3 endpoint (for MinIO)
#   AWS_DEFAULT_REGION — AWS region (default: us-east-1)
#
# S3 key pattern: backups/{yyyy-mm-dd}/summa_{timestamp}.sql.gz
#
# Retention: use S3 lifecycle rules (see docs/MONITORING.md).
#
# Usage:
#   ./scripts/ops/backup_db.sh
#
# Cron (nightly 3am UTC):
#   0 3 * * * docker compose exec -T api /app/scripts/ops/backup_db.sh >> /var/log/backup.log 2>&1
# ============================================================================

set -euo pipefail

# --- Configuration ---
DATE="$(date -u +%Y-%m-%d)"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
DUMP_FILE="/tmp/summa_${TIMESTAMP}.sql.gz"
S3_KEY="backups/${DATE}/summa_${TIMESTAMP}.sql.gz"

# --- Cleanup on exit (even on failure) ---
trap 'rm -f "${DUMP_FILE}"' EXIT

# --- Validate required vars ---
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL is not set" >&2
    exit 1
fi

if [ -z "${BACKUP_S3_BUCKET:-}" ]; then
    echo "ERROR: BACKUP_S3_BUCKET is not set" >&2
    exit 1
fi

# --- S3 args (bash array — no word-splitting risk) ---
S3_ARGS=()
if [ -n "${S3_ENDPOINT_URL:-}" ]; then
    S3_ARGS+=(--endpoint-url "${S3_ENDPOINT_URL}")
fi

# --- Convert async driver URL to sync for pg_dump ---
# Assumes format: postgresql+asyncpg://user:pass@host:port/dbname
# pg_dump needs: postgresql://user:pass@host:port/dbname
PG_URL=$(echo "${DATABASE_URL}" | sed 's|postgresql+asyncpg://|postgresql://|')

echo "[$(date -Iseconds)] Starting backup..."

# --- Dump and compress ---
pg_dump "${PG_URL}" | gzip > "${DUMP_FILE}"
DUMP_SIZE=$(du -h "${DUMP_FILE}" | cut -f1)
echo "[$(date -Iseconds)] Dump created: ${DUMP_FILE} (${DUMP_SIZE})"

# --- Upload to S3 ---
aws s3 cp "${DUMP_FILE}" "s3://${BACKUP_S3_BUCKET}/${S3_KEY}" "${S3_ARGS[@]}"
echo "[$(date -Iseconds)] Uploaded to s3://${BACKUP_S3_BUCKET}/${S3_KEY}"

# --- Retention ---
# Auto-deletion removed for safety. Use S3 lifecycle rules instead.
# See docs/MONITORING.md for setup instructions and verification commands.

echo "[$(date -Iseconds)] Backup complete."