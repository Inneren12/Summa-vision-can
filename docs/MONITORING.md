# Monitoring & Alerting

## Health Endpoints

| Endpoint | Purpose | Expected | Alert if |
|----------|---------|----------|----------|
| `GET /api/health` | Liveness | 200 always | 5xx for >5 minutes |
| `GET /api/health/ready` | Readiness | 200 when DB + temp OK | 503 for >2 minutes |

## Logging

- **Production:** JSON lines to stdout (`LOG_FORMAT=json`).
  Ship to CloudWatch Logs, Loki, or ELK via Docker log driver.
- **Development:** Colored console output (`LOG_FORMAT=console`).

Log levels used in the application:
- `INFO` — normal operations (app_started, job_claimed, job_succeeded)
- `WARNING` — recoverable issues (zombie_reaper_requeued, data_quality_warning,
  cool_down_active, shutdown_timeout)
- `ERROR` — job failures, unhandled exceptions
- `CRITICAL` — data contract violations, configuration errors

## Alerts (Baseline)

### 1. API Health Failure

**What:** `/api/health` returns non-200 or is unreachable.
**Threshold:** 5 minutes of consecutive failures.
**Setup options:**
- Cloudflare Uptime Monitor → webhook / email
- AWS CloudWatch Synthetics canary
- UptimeRobot (free tier sufficient for MVP)

### 2. Job Failure Rate Spike

**What:** Too many jobs failing in a short window.
**Threshold:** >5 failed jobs in 10 minutes.
**Detection:** Query AuditEvent table:

```sql
SELECT COUNT(*)
FROM audit_events
WHERE event_type = 'job.failed'
  AND created_at > NOW() - INTERVAL '10 minutes';
```

**Setup options:**
- Cron job running this query every 10 minutes → send alert if count > 5
- Future: Grafana alert rule on this query

### 3. Backup Failure

**What:** Nightly backup script exits non-zero.
**Detection:** Cron output goes to log file. If log contains "ERROR"
or backup file not found in S3 for today's date.
**Setup:**
- Wrap cron entry: `backup_db.sh || curl -fsS -X POST "${ALERT_WEBHOOK_URL}" -d '{"text":"Backup failed"}'`
- Or use healthcheck.io / cronitor.io for dead man's switch monitoring

## Operational Queries

### Recent job failures:
```sql
SELECT job_type, error_code, COUNT(*) as failures,
       MAX(finished_at) as last_failure
FROM jobs
WHERE status = 'failed'
  AND finished_at > NOW() - INTERVAL '24 hours'
GROUP BY job_type, error_code
ORDER BY failures DESC;
```

### Lead capture funnel (last 7 days):
```sql
SELECT event_type, COUNT(*) as count
FROM audit_events
WHERE event_type IN ('lead.captured', 'lead.email_sent',
                     'token.activated', 'token.exhausted')
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY event_type;
```

### Data contract violations (indicates StatCan format change):
```sql
SELECT ae.entity_id as job_id,
       ae.metadata_json,
       ae.created_at
FROM audit_events ae
WHERE ae.event_type = 'data.contract_violation'
ORDER BY ae.created_at DESC
LIMIT 10;
```

## Backup Verification

### Verify latest backup exists:
```bash
aws s3 ls s3://${BACKUP_S3_BUCKET}/backups/$(date +%Y-%m-%d)/
```

### Restore from backup (test procedure):
```bash
# Download latest
aws s3 cp s3://${BACKUP_S3_BUCKET}/backups/2025-04-04/summa_20250404_030000.sql.gz /tmp/restore.sql.gz

# Decompress
gunzip /tmp/restore.sql.gz

# Restore to test database
psql postgresql://summa:password@localhost:5432/summa_test < /tmp/restore.sql

# Verify
psql postgresql://summa:password@localhost:5432/summa_test \
    -c "SELECT COUNT(*) FROM publications; SELECT COUNT(*) FROM jobs;"
```
