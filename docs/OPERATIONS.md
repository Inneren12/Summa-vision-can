# Operations Guide

## Deployment

### First deploy:
```bash
# 1. Set up environment variables (never commit secrets)
export DATABASE_URL=postgresql+asyncpg://summa:SECURE_PASSWORD@db:5432/summa
export ADMIN_API_KEY=SECURE_RANDOM_KEY
export S3_BUCKET=summa-vision-prod
export CDN_BASE_URL=https://cdn.summa.vision
export LOG_FORMAT=json
export BACKUP_S3_BUCKET=summa-vision-backups

# 2. Start services
docker compose up -d

# 3. Run migrations
docker compose exec api alembic upgrade head

# 4. Verify
curl https://api.summa.vision/api/health
curl https://api.summa.vision/api/health/ready
```

### Subsequent deploys:
```bash
docker compose pull api
docker compose up -d api
# Migrations run automatically if entrypoint is configured,
# otherwise run manually:
docker compose exec api alembic upgrade head
```

## Backup

- **Schedule:** Nightly at 3:00 AM UTC
- **Retention:** 30 days (configurable via `BACKUP_RETENTION_DAYS`)
- **Storage:** S3 bucket `${BACKUP_S3_BUCKET}`
- **Key pattern:** `backups/{yyyy-mm-dd}/summa_{timestamp}.sql.gz`

### Setup cron:
```bash
crontab -e
# Add:
0 3 * * * docker compose exec -T api /app/scripts/ops/backup_db.sh >> /var/log/summa-backup.log 2>&1
```

### Manual backup:
```bash
docker compose exec api /app/scripts/ops/backup_db.sh
```

## Secret Management

| Environment | Storage | Rule |
|-------------|---------|------|
| Development | `.env` file (git-ignored) | Never commit |
| Production | Shell env vars / deploy system | No `.env` on server |

### Required secrets by stage:

**Étape 0 (Infrastructure):**
- `DATABASE_URL`
- `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD` — required by compose `db` service. Compose fails to start if any are unset (no fallback defaults).
- `ADMIN_API_KEY`
- `S3_BUCKET`, S3 credentials
- `BACKUP_S3_BUCKET`

**Étape D (Public site):**
- `TURNSTILE_SECRET_KEY`
- Email provider credentials (SES/Resend)
- `CDN_BASE_URL` (production CDN)

### Secret rotation:
1. Generate new secret
2. Update environment variable on server
3. Restart affected service: `docker compose restart api`
4. Verify health: `curl /api/health/ready`

## Job Administration

### View job queue:
```bash
docker compose exec api python3 -c "
import asyncio
from src.core.database import async_session_factory
from src.repositories.job_repository import JobRepository

async def show():
    async with async_session_factory() as s:
        repo = JobRepository(s)
        jobs = await repo.list_jobs(limit=20)
        for j in jobs:
            print(f'{j.id:4d} | {j.job_type:20s} | {j.status.value:8s} | {j.created_at}')

asyncio.run(show())
"
```

### Retry a failed job:
Currently done by re-enqueueing via API endpoint.
Jobs dashboard (Étape C) will provide a UI for this.

## Troubleshooting

### API not responding:
```bash
docker compose logs api --tail=50
docker compose exec api curl http://localhost:8000/api/health/ready
```

### Stale jobs after restart:
Zombie reaper runs automatically on startup. Check logs:
```bash
docker compose logs api | grep zombie_reaper
```

### Database connection issues:
```bash
docker compose exec api python3 -c "
import os
from sqlalchemy import create_engine, text
url = os.environ['DATABASE_URL'].replace('+asyncpg', '')
e = create_engine(url)
with e.connect() as c:
    print(c.execute(text('SELECT 1')).scalar())
"
```

## Migrations not safe to roll back

### Phase 2.2.0 lineage_key migration — forward-only after Phase 2.3

**Status:** Active operational constraint as of 2026-04-28.
**Cross-ref:** DEBT-046 (full impact analysis), `docs/recon/phase-2-2-0-recon.md` §B4 (Phase 2.2.0 architectural decision).

#### Constraint

Once Phase 2.3 ships and starts logging `?utm_content=<lineage_key>` on
lead funnel URLs, the lineage_key migration becomes effectively
forward-only.

#### Why

- `generate_lineage_key()` uses UUID v7, which is non-deterministic
  (timestamp + randomness).
- Downgrading the migration drops the `lineage_key` column.
- Re-upgrading regenerates fresh root keys for every row.
- Historical UTM data in the `Lead` table or audit logs records keys
  that no longer match any current row → attribution breaks silently.

#### Operational rule

**Do NOT downgrade the lineage_key migration in production once Phase
2.3 has logged its first UTM-tagged lead.**

If downgrade becomes necessary (emergency rollback, schema rewrite,
etc.):

1. Snapshot the current `publications.lineage_key` column to a backup
   table BEFORE downgrade:

   ```sql
   CREATE TABLE publications_lineage_backup_<YYYYMMDD> AS
       SELECT id, lineage_key FROM publications;
   ```

2. Perform downgrade as needed.

3. After re-upgrade, write a one-shot script to restore lineage_keys:

   ```sql
   UPDATE publications p
   SET lineage_key = b.lineage_key
   FROM publications_lineage_backup_<YYYYMMDD> b
   WHERE p.id = b.id;
   ```

4. Verify UTM attribution resumes via spot-check on recent leads.

The restore script does NOT exist today. It would be written on-demand
if downgrade becomes necessary.

#### Pre-Phase-2.3 (current state)

Until Phase 2.3 ships, downgrading is safe — no UTM data is recorded
yet. The constraint activates with Phase 2.3 release.
