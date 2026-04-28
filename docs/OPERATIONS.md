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
