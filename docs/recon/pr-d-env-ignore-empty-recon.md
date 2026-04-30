# PR-D Recon — `env_ignore_empty=True` Safety Audit

## Section 1 — Settings field inventory

Source audited: `backend/src/core/config.py` (full file).  
Current `model_config` is on line 171.

| Field | Type | Python default | Env var name (if non-default) | Required by validator |
|---|---|---|---|---|
| app_name | str | "Summa Vision API" | default `APP_NAME` | no |
| debug | bool | `False` | default `DEBUG` | no |
| cors_origins | str | "*" | default `CORS_ORIGINS` | indirectly (production path uses truthy check only for `cdn_base_url`/`public_site_url`, not this field) |
| environment | str | "development" | default `ENVIRONMENT` | yes (controls prod-only required checks) |
| log_format | str | "console" | default `LOG_FORMAT` | no |
| database_url | str | `postgresql+asyncpg://summa:devpassword@localhost:5432/summa` | default `DATABASE_URL` | yes (`if not self.database_url`) |
| max_preview_rows | int | `100` | default `MAX_PREVIEW_ROWS` | no |
| max_chart_points | int | `500` | default `MAX_CHART_POINTS` | no |
| max_zip_size_mb | int | `100` | default `MAX_ZIP_SIZE_MB` | no |
| max_export_rows | int | `250000` | default `MAX_EXPORT_ROWS` | no |
| max_token_uses | int | `5` | default `MAX_TOKEN_USES` | no |
| magic_token_ttl_hours | int | `48` | default `MAGIC_TOKEN_TTL_HOURS` | no |
| signed_url_ttl_minutes | int | `10` | default `SIGNED_URL_TTL_MINUTES` | no |
| max_job_retries | int | `3` | default `MAX_JOB_RETRIES` | no |
| polars_max_threads | int | `2` | default `POLARS_MAX_THREADS` | no |
| backup_s3_bucket | str | "" | default `BACKUP_S3_BUCKET` | no |
| backup_retention_days | int | `30` | default `BACKUP_RETENTION_DAYS` | no |
| storage_backend | `Literal["s3", "local"]` | "local" | default `STORAGE_BACKEND` | validated by type + used by branching logic |
| s3_bucket | str | "summa-vision-dev" | default `S3_BUCKET` | yes (`if not self.s3_bucket`) |
| s3_endpoint_url | str | "" | default `S3_ENDPOINT_URL` | no |
| s3_access_key_id | str | "" | default `S3_ACCESS_KEY_ID` | no |
| s3_secret_access_key | str | "" | default `S3_SECRET_ACCESS_KEY` | no |
| s3_region | str | "us-east-1" | default `S3_REGION` | no |
| cdn_base_url | str | "http://localhost:9000/summa-vision-dev" | default `CDN_BASE_URL` | yes in production (`if not self.cdn_base_url`) |
| local_storage_dir | str | "./data/local_storage" | default `LOCAL_STORAGE_DIR` | no |
| scheduler_db_url | str | "sqlite:///data/jobs.sqlite" | default `SCHEDULER_DB_URL` | no |
| scheduler_enabled | bool | `True` | default `SCHEDULER_ENABLED` | no |
| temp_upload_ttl_hours | int | `24` (`Field(ge=1)`) | default `TEMP_UPLOAD_TTL_HOURS` | no |
| temp_upload_cleanup_interval_minutes | int | `60` (`Field(ge=5)`) | default `TEMP_UPLOAD_CLEANUP_INTERVAL_MINUTES` | no |
| temp_cleanup_max_delete_keys_per_cycle | int | `1000` (`Field(ge=1, le=10000)`) | default `TEMP_CLEANUP_MAX_DELETE_KEYS_PER_CYCLE` | no |
| temp_cleanup_max_list_keys_per_cycle | int | `50000` (`Field(ge=1000, le=1000000)`) | default `TEMP_CLEANUP_MAX_LIST_KEYS_PER_CYCLE` | no |
| temp_cleanup_prefixes | `list[str]` | `["temp/uploads/"]` via `default_factory` | default `TEMP_CLEANUP_PREFIXES` | no |
| audit_retention_days | int | `90` | default `AUDIT_RETENTION_DAYS` | no |
| admin_api_key | str | "" | default `ADMIN_API_KEY` | yes (`if not self.admin_api_key`) |
| turnstile_secret_key | str | "" | default `TURNSTILE_SECRET_KEY` | yes in production (`if not self.turnstile_secret_key`) |
| public_site_url | str | "http://localhost:3000" | default `PUBLIC_SITE_URL` | yes in production (`if not self.public_site_url`) |
| SLACK_WEBHOOK_URL | str | "" | default `SLACK_WEBHOOK_URL` | no |
| BEEHIIV_API_KEY | str | "" | default `BEEHIIV_API_KEY` | no |
| BEEHIIV_PUBLICATION_ID | str | "" | default `BEEHIIV_PUBLICATION_ID` | no |

No `validation_alias`/`alias` overrides found in Settings fields.

Verbatim validator region (ambiguity-sensitive):

```python
if not self.database_url:
    errors.append("DATABASE_URL is required")
if not self.admin_api_key:
    errors.append("ADMIN_API_KEY is required")
if not self.s3_bucket:
    errors.append("S3_BUCKET is required")

if self.environment == "production":
    if not self.cdn_base_url:
        errors.append("CDN_BASE_URL is required in production")
    if not self.public_site_url:
        errors.append("PUBLIC_SITE_URL is required in production")
    if not self.turnstile_secret_key:
        errors.append("TURNSTILE_SECRET_KEY is required in production")
```

## Section 2 — Empty-string semantics audit

String-emptiness checks found in `backend/src` tied to settings-derived values:

1. `backend/src/core/config.py:147,149,151,157,159,161`
   - Fields: `database_url`, `admin_api_key`, `s3_bucket`, `cdn_base_url`, `public_site_url`, `turnstile_secret_key`
   - Behavior on empty: **raises error** (`ValueError` during Settings validation).
   - Reachability from env today (`env_ignore_empty=False`): empty env is reachable and triggers validator failure.
   - With `env_ignore_empty=True`: empty env for non-empty-default fields becomes default, reducing accidental failure (except defaults that are empty remain empty and still fail if required).

2. `backend/src/services/notifications/slack.py:61`
   - Field lineage: `settings.SLACK_WEBHOOK_URL` copied to `self.webhook_url`.
   - Check: `if not self.webhook_url:`
   - Behavior on empty: **treats as disabled/skip**, logs one warning, returns `False`.
   - Reachability from env: yes, but default is already empty string; `env_ignore_empty=True` does not change effective behavior.

No direct checks found like `if settings.<field> == ""` for non-empty-default Settings fields outside validator.

## Section 3 — Critical fields per-field analysis (non-empty Python defaults)

### Field: `app_name`
Python default: `"Summa Vision API"`.

Audit findings: consumed in `main.py` to set FastAPI title (`title=settings_on_startup.app_name`). No emptiness checks found.

Risk with `APP_NAME=""`: today app title becomes empty string; after change it would revert to default title. No logic branching impact.

Verdict: **SAFE**.

### Field: `cors_origins`
Python default: `"*"`.

Audit findings: field declared but not consumed in runtime CORS middleware; CORS origins are hardcoded list in `main.py` from environment gate, not `settings.cors_origins`.

Risk with `CORS_ORIGINS=""`: effectively no current runtime impact from this field (appears unused).

Verdict: **SAFE** (and currently unused).

### Field: `environment`
Python default: `"development"`.

Audit findings: used for docs/OpenAPI exposure and localhost CORS gate in `main.py`, and as production switch in `validate_required_secrets`.

Risk with `ENVIRONMENT=""`: today empty means not equal `"production"` so app behaves as non-prod and skips prod-only secret checks; after change empty becomes `"development"`, same branch outcomes.

Verdict: **SAFE**.

### Field: `log_format`
Python default: `"console"`.

Audit findings: used in logging setup: `use_json = force_json or log_format == "json"`.

Risk with `LOG_FORMAT=""`: today resolves to console branch (`"" != "json"`); after change falls back to `"console"`, same branch.

Verdict: **SAFE**.

### Field: `database_url`
Python default: non-empty Postgres DSN.

Audit findings: validator enforces non-empty; DB engine uses resulting value.

Risk with `DATABASE_URL=""`: today hard-fails validation; after change empty becomes default DSN and passes. This is behavior change, but it removes accidental empty override failure and matches intended default semantics.

Verdict: **SAFE**.

### Field: `storage_backend` (Literal)
Python default: `"local"`.

Audit findings: storage factory branches on value (`local`/`s3`), runtime guard raises for unknown.

Risk with `STORAGE_BACKEND=""`: today fails Pydantic Literal validation; after change empty treated as unset and falls back to `"local"`.

Verdict: **SAFE** (strictly safer failure mode for accidental empties).

### Field: `s3_bucket`
Python default: `"summa-vision-dev"`.

Audit findings: validator enforces non-empty always.

Risk with `S3_BUCKET=""`: today validation failure; after change empty falls back default and passes.

Verdict: **SAFE**.

### Field: `s3_region`
Python default: `"us-east-1"`.

Audit findings: passed into S3 storage manager; no emptiness checks.

Risk with `S3_REGION=""`: today empty string flows to client config; after change reverts to `us-east-1`.

Verdict: **SAFE**.

### Field: `cdn_base_url`
Python default: `"http://localhost:9000/summa-vision-dev"`.

Audit findings: used to build email image URLs; production validator requires non-empty.

Risk with `CDN_BASE_URL=""`: today in dev yields malformed `/path`-style URLs but no startup failure; in production causes startup validation failure. After change empty falls back to default, avoiding both. No code path uses empty as meaningful sentinel.

Verdict: **SAFE**.

### Field: `local_storage_dir`
Python default: `"./data/local_storage"`.

Audit findings: used when local storage backend selected. No emptiness checks.

Risk with `LOCAL_STORAGE_DIR=""`: today passes empty to LocalStorageManager; after change default path restored.

Verdict: **SAFE**.

### Field: `scheduler_db_url`
Python default: `"sqlite:///data/jobs.sqlite"`.

Audit findings: used as job store DB URL; no emptiness checks.

Risk with `SCHEDULER_DB_URL=""`: today could misconfigure job store; after change defaults correctly.

Verdict: **SAFE**.

### Field: `public_site_url`
Python default: `"http://localhost:3000"`.

Audit findings: used to build magic links; required non-empty in production.

Risk with `PUBLIC_SITE_URL=""`: today empty yields relative-ish broken links in non-prod and startup failure in prod; after change default URL used.

Verdict: **SAFE**.

## Section 4 — Tests audit

Discovered tests:
- `backend/tests/core/test_config.py`

Coverage found:
- Required-secret validator failures for empty explicit values (`database_url`, `admin_api_key`, `s3_bucket`).
- Production-only requirements for `cdn_base_url`, `public_site_url`, `turnstile_secret_key` empties.
- Positive tests for dev/prod valid configs.

`Settings()` construction via env loading is **not** covered (no tests found that instantiate bare `Settings()` with environment patching).

Empty env-string handling coverage:
- No test found that sets OS env vars to `""` and asserts parse/default behavior.

Gaps for impl PR:
1. empty env var + `env_ignore_empty=True` => Python default applies.
2. unset env var => Python default applies (regression).
3. explicit non-empty env var => env value wins.
4. Literal case: `STORAGE_BACKEND=""` should now resolve to default `"local"` (no validation error).

## Section 5 — pydantic-settings version + behavior verification

Dependency declaration:
- `backend/pyproject.toml` contains `pydantic-settings>=2.0,<3.0.0`.

Empirical behavior check:
- `docker compose exec` command could not run in this environment (`docker: command not found`).
- Fallback local Python reproduction executed successfully.

Actual output:

```text
version: 2.14.0
with env_ignore_empty=True, FOO="": 'default_value'
with FOO unset: 'default_value'
with FOO="explicit": 'explicit'
```

Result: behavior matches expected semantics.

## Section 6 — Compose cleanup scope (informational)

Search run: `grep -nE "\$\{[A-Z_]+:-[^}]+\}" docker-compose.yml`.

Result: no matches in `docker-compose.yml` in this checkout.

Informational implication: no `${VAR:-default}` entries were detected in that file to classify for PR-E cleanup.

## Section 7 — Verdict

`PR-D Safety Verdict: SAFE`

- All non-empty-default fields were audited for consumers and empty-string handling.
- No intentional runtime semantics were found that rely on an empty-string value for those fields.
- Where behavior changes, it is from accidental empty override / validation failure toward documented defaults.
- Literal field behavior (`storage_backend`) becomes safer for accidental empty env values.

## Section 8 — Open questions for founder

1. `cors_origins` is currently declared in `Settings` but runtime CORS middleware in `main.py` uses a hardcoded list; should this field remain intentionally unused?
2. Should PR-D include explicit tests for env-var parsing (not only direct constructor kwargs) in `backend/tests/core/test_config.py`?
3. For required-in-production fields (`cdn_base_url`, `public_site_url`, `turnstile_secret_key`), do you want dedicated regression tests that prove `ENV_VAR=""` falls back to defaults with `env_ignore_empty=True`?

## Section 9 — Reading list for impl prompt

Primary code target:
- `backend/src/core/config.py:171` (`model_config` one-line addition).

Test file target:
- `backend/tests/core/test_config.py` (extend with env-behavior tests).

No other file changes indicated by this safety recon.
