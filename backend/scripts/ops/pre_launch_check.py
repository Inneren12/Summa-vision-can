"""
Pre-launch readiness checker for Summa Vision.
Run: python -m scripts.ops.pre_launch_check

Checks all infrastructure dependencies, configs, and critical flows.
Exit code 0 = all green, 1 = failures found.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

import httpx
from sqlalchemy import func, select, text

from src.core.config import Settings, get_settings
from src.core.database import get_engine, get_session_factory
from src.core.storage import get_storage_manager
from src.models.audit_event import AuditEvent
from src.models.job import Job, JobStatus
from src.models.publication import Publication, PublicationStatus


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    ok: bool
    warning: bool = False
    message: str = ""

    @staticmethod
    def passed(message: str = "") -> CheckResult:
        return CheckResult(ok=True, message=message)

    @staticmethod
    def warn(message: str) -> CheckResult:
        return CheckResult(ok=True, warning=True, message=message)

    @staticmethod
    def fail(message: str) -> CheckResult:
        return CheckResult(ok=False, message=message)


# ---------------------------------------------------------------------------
# Shared state (set once in run_all_checks)
# ---------------------------------------------------------------------------

_args: argparse.Namespace | None = None


# ---------------------------------------------------------------------------
# Group 1: Configuration
# ---------------------------------------------------------------------------


async def check_required_env_vars() -> CheckResult:
    """Verify all required env vars are set and non-empty."""
    settings = get_settings()

    required: dict[str, str] = {
        "DATABASE_URL": settings.database_url,
        "ADMIN_API_KEY": settings.admin_api_key,
        "S3_BUCKET": settings.s3_bucket,
        "CDN_BASE_URL": settings.cdn_base_url,
        "PUBLIC_SITE_URL": settings.public_site_url,
        "TURNSTILE_SECRET_KEY": settings.turnstile_secret_key,
    }

    recommended: dict[str, str] = {
        "SLACK_WEBHOOK_URL": settings.SLACK_WEBHOOK_URL,
        "BEEHIIV_API_KEY": settings.BEEHIIV_API_KEY,
    }

    missing_required = [k for k, v in required.items() if not v]
    missing_recommended = [k for k, v in recommended.items() if not v]

    if missing_required:
        return CheckResult.fail(f"Missing required: {', '.join(missing_required)}")
    if missing_recommended:
        return CheckResult.warn(
            f"Missing recommended: {', '.join(missing_recommended)}"
        )
    return CheckResult.passed()


# ---------------------------------------------------------------------------
# Group 2: Database
# ---------------------------------------------------------------------------


async def check_database_connection() -> CheckResult:
    """Verify DB is reachable and migrations are up to date."""
    engine = get_engine()

    async with engine.connect() as conn:
        # 1. Basic connectivity
        result = await conn.execute(text("SELECT 1"))
        if result.scalar() != 1:
            return CheckResult.fail("SELECT 1 did not return 1")

        # 2. Alembic revision
        current_rev: str | None = None
        try:
            rev = await conn.execute(
                text("SELECT version_num FROM alembic_version")
            )
            current_rev = rev.scalar_one_or_none()
            if current_rev is None:
                return CheckResult.warn(
                    "alembic_version table empty — no migrations applied"
                )
        except Exception:
            return CheckResult.warn(
                "alembic_version table not found — migrations may not be managed"
            )

        # 3. Count user tables
        table_count_row = await conn.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        )
        count = table_count_row.scalar()
        if count == 0:
            return CheckResult.fail("No tables found in public schema")

    return CheckResult.passed(f"revision={current_rev}, {count} tables")


async def check_database_tables() -> CheckResult:
    """Verify all expected tables exist."""
    expected = [
        "publications",
        "leads",
        "download_tokens",
        "jobs",
        "audit_events",
        "cube_catalog",
    ]

    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        )
        existing = {row[0] for row in result.fetchall()}

    missing = [t for t in expected if t not in existing]
    if missing:
        return CheckResult.fail(f"Missing tables: {', '.join(missing)}")
    return CheckResult.passed(f"All {len(expected)} expected tables present")


# ---------------------------------------------------------------------------
# Group 3: Storage (S3/MinIO)
# ---------------------------------------------------------------------------


async def check_s3_connection() -> CheckResult:
    """Verify S3 bucket is accessible with round-trip test."""
    settings = get_settings()
    storage = get_storage_manager(settings)

    test_key = "_health_check/pre_launch_test.txt"
    test_content = f"pre-launch check {datetime.now(timezone.utc).isoformat()}"

    # 1. Upload
    await storage.upload_raw(test_content, test_key, content_type="text/plain")

    # 2. Download and verify
    downloaded = await storage.download_bytes(test_key)
    if downloaded.decode() != test_content:
        return CheckResult.fail("S3 round-trip content mismatch")

    # 3. Delete
    await storage.delete_object(test_key)

    # 4. CDN reachability
    cdn_url = settings.cdn_base_url
    if cdn_url:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.head(cdn_url, follow_redirects=True)
                if resp.status_code >= 500:
                    return CheckResult.warn(f"CDN returned {resp.status_code}")
        except httpx.ConnectError:
            return CheckResult.warn(f"CDN unreachable: {cdn_url}")

    return CheckResult.passed()


async def check_s3_key_structure() -> CheckResult:
    """Verify expected S3 prefixes exist and report object counts."""
    settings = get_settings()
    storage = get_storage_manager(settings)

    prefixes = ["publications/", "statcan/raw/", "statcan/processed/"]
    report_parts: list[str] = []
    pub_count = 0

    for prefix in prefixes:
        try:
            objects = await storage.list_objects(prefix)
            report_parts.append(f"{prefix} = {len(objects)}")
            if prefix == "publications/":
                pub_count = len(objects)
        except Exception:
            report_parts.append(f"{prefix} = ERROR")

    detail = "; ".join(report_parts)

    if pub_count < 10:
        return CheckResult.warn(
            f"publications/ has {pub_count} objects (target: 10+). {detail}"
        )

    return CheckResult.passed(detail)


# ---------------------------------------------------------------------------
# Group 4: API Health
# ---------------------------------------------------------------------------


async def check_api_health() -> CheckResult:
    """Verify API endpoints respond correctly."""
    assert _args is not None
    api_url = _args.api_url

    async with httpx.AsyncClient(timeout=10) as client:
        # 1. Liveness
        resp = await client.get(f"{api_url}/api/health")
        if resp.status_code != 200:
            return CheckResult.fail(f"/api/health returned {resp.status_code}")

        # 2. Readiness
        resp = await client.get(f"{api_url}/api/health/ready")
        if resp.status_code != 200:
            return CheckResult.fail(f"/api/health/ready returned {resp.status_code}")

        # 3. Gallery
        resp = await client.get(f"{api_url}/api/v1/public/graphics?limit=1")
        if resp.status_code != 200:
            return CheckResult.fail(
                f"/api/v1/public/graphics returned {resp.status_code}"
            )

        # 4. CORS headers on preflight
        resp = await client.options(
            f"{api_url}/api/v1/public/graphics",
            headers={
                "Origin": "https://summa.vision",
                "Access-Control-Request-Method": "GET",
            },
        )
        acl = resp.headers.get("access-control-allow-origin", "")
        if not acl:
            return CheckResult.warn("CORS headers missing on public endpoint")

    return CheckResult.passed()


async def check_admin_auth() -> CheckResult:
    """Verify admin auth rejects unauthenticated and accepts valid key."""
    assert _args is not None
    api_url = _args.api_url
    settings = get_settings()

    async with httpx.AsyncClient(timeout=10) as client:
        # 1. Without key — must reject
        resp = await client.get(f"{api_url}/api/v1/admin/jobs")
        if resp.status_code not in (401, 403):
            return CheckResult.fail(
                f"Admin without key returned {resp.status_code} (expected 401/403)"
            )

        # 2. With correct key — must succeed
        resp = await client.get(
            f"{api_url}/api/v1/admin/jobs",
            headers={"X-API-KEY": settings.admin_api_key},
        )
        if resp.status_code != 200:
            return CheckResult.fail(
                f"Admin with key returned {resp.status_code} (expected 200)"
            )

    return CheckResult.passed()


# ---------------------------------------------------------------------------
# Group 5: Email
# ---------------------------------------------------------------------------


async def check_email_service() -> CheckResult:
    """Verify email sending works (actually sends a test email)."""
    settings = get_settings()

    if settings.environment == "development":
        return CheckResult.warn(
            "Development mode — using ConsoleEmailService (no real email sent)"
        )

    # Attempt to instantiate the production email service
    from src.services.email.interface import EmailServiceInterface  # noqa: F811

    service: EmailServiceInterface | None = None
    try:
        from src.services.email.ses import SESEmailService

        service = SESEmailService(settings)
    except (ImportError, Exception):
        pass

    if service is None:
        try:
            from src.services.email.resend_service import ResendEmailService

            service = ResendEmailService(settings)
        except (ImportError, Exception):
            pass

    if service is None:
        return CheckResult.warn("No production email service module available")

    now = datetime.now(timezone.utc).isoformat()
    await service.send_email(
        to="prelaunch-test@summa-test.local",
        subject="[Summa Vision] Pre-launch test",
        html_body=f"<p>If you receive this, email is working. Timestamp: {now}</p>",
    )

    return CheckResult.passed("Test email sent successfully")


# ---------------------------------------------------------------------------
# Group 6: Turnstile
# ---------------------------------------------------------------------------


async def check_turnstile() -> CheckResult:
    """Verify Turnstile secret key is set and valid format."""
    settings = get_settings()
    key = settings.turnstile_secret_key

    if not key:
        return CheckResult.fail("TURNSTILE_SECRET_KEY is not set")

    if not key.startswith("0x"):
        return CheckResult.warn(
            f"TURNSTILE_SECRET_KEY doesn't start with '0x' "
            f"(starts with '{key[:4]}...')"
        )

    # Verify Cloudflare siteverify API is reachable
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": key,
                "response": "1x0000000000000000000000000000000AA",
            },
        )
        if resp.status_code != 200:
            return CheckResult.fail(
                f"Turnstile API returned {resp.status_code}"
            )

    return CheckResult.passed()


# ---------------------------------------------------------------------------
# Group 7: Publications
# ---------------------------------------------------------------------------


async def check_publications_exist() -> CheckResult:
    """Verify at least 10 published graphics exist (D-5 requirement)."""
    settings = get_settings()
    factory = get_session_factory()
    storage = get_storage_manager(settings)

    async with factory() as session:
        # Total published count
        result = await session.execute(
            select(func.count(Publication.id)).where(
                Publication.status == PublicationStatus.PUBLISHED
            )
        )
        pub_count = result.scalar() or 0

        if pub_count == 0:
            return CheckResult.fail("No published graphics found")

        # Sample up to 10 for S3 + CDN validation
        pubs = (
            await session.execute(
                select(Publication)
                .where(Publication.status == PublicationStatus.PUBLISHED)
                .limit(10)
            )
        ).scalars().all()

    s3_valid = 0
    cdn_valid = 0

    for pub in pubs:
        if not pub.s3_key_lowres:
            continue
        # S3 check
        try:
            await storage.download_bytes(pub.s3_key_lowres)
            s3_valid += 1
        except Exception:
            pass
        # CDN check
        if settings.cdn_base_url:
            cdn_url = f"{settings.cdn_base_url.rstrip('/')}/{pub.s3_key_lowres}"
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.head(cdn_url, follow_redirects=True)
                    if resp.status_code in (200, 301, 302):
                        cdn_valid += 1
            except Exception:
                pass

    sampled = len(pubs)
    detail = (
        f"{pub_count} published, "
        f"{s3_valid}/{sampled} S3 valid, "
        f"{cdn_valid}/{sampled} CDN valid"
    )

    if pub_count < 10:
        return CheckResult.fail(f"Only {pub_count} published (need 10). {detail}")

    return CheckResult.passed(detail)


# ---------------------------------------------------------------------------
# Group 8: Job System
# ---------------------------------------------------------------------------


async def check_job_system() -> CheckResult:
    """Verify job system is operational."""
    factory = get_session_factory()
    now = datetime.now(timezone.utc)

    async with factory() as session:
        # 1. Stuck jobs (running > 10 min)
        threshold = now - timedelta(minutes=10)
        stuck_count = (
            await session.execute(
                select(func.count(Job.id)).where(
                    Job.status == JobStatus.RUNNING,
                    Job.started_at < threshold,
                )
            )
        ).scalar() or 0

        # 2. Recent (24h) job stats
        since = now - timedelta(hours=24)
        total_jobs = (
            await session.execute(
                select(func.count(Job.id)).where(Job.created_at >= since)
            )
        ).scalar() or 0

        success_jobs = (
            await session.execute(
                select(func.count(Job.id)).where(
                    Job.status == JobStatus.SUCCESS,
                    Job.created_at >= since,
                )
            )
        ).scalar() or 0

        # 3. Recent audit events
        recent_audits = (
            await session.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.created_at >= since
                )
            )
        ).scalar() or 0

    issues: list[str] = []
    if stuck_count > 0:
        issues.append(f"{stuck_count} stuck jobs (running >10 min)")
    if total_jobs > 0:
        rate = (success_jobs / total_jobs) * 100
        if rate < 80:
            issues.append(
                f"Low success rate: {rate:.0f}% ({success_jobs}/{total_jobs})"
            )
    if recent_audits == 0:
        issues.append("No audit events in last 24h")

    detail = (
        f"24h: {total_jobs} jobs ({success_jobs} success), "
        f"{recent_audits} audit events"
    )

    if stuck_count > 0:
        return CheckResult.fail("; ".join(issues))
    if issues:
        return CheckResult.warn(f"{'; '.join(issues)} — {detail}")

    return CheckResult.passed(detail)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _skip_check(reason: str) -> Callable[[], Awaitable[CheckResult]]:
    """Return a coroutine that produces a warning-skip result."""

    async def _skipped() -> CheckResult:
        return CheckResult.warn(f"skipped ({reason})")

    return _skipped


async def run_all_checks(args: argparse.Namespace) -> int:
    global _args
    _args = args

    checks: list[tuple[str, Callable[[], Awaitable[CheckResult]]]] = [
        ("Configuration", check_required_env_vars),
        ("Database Connection", check_database_connection),
        ("Database Tables", check_database_tables),
        ("S3 Storage", check_s3_connection),
        ("S3 Key Structure", check_s3_key_structure),
        ("API Health", check_api_health),
        ("Admin Auth", check_admin_auth),
        (
            "Email Service",
            check_email_service
            if not args.skip_email
            else _skip_check("--skip-email"),
        ),
        ("Turnstile", check_turnstile),
        ("Publications (\u226510)", check_publications_exist),
        ("Job System", check_job_system),
    ]

    print("=" * 60)
    print("  SUMMA VISION \u2014 PRE-LAUNCH READINESS CHECK")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    warnings = 0

    for name, check_fn in checks:
        try:
            result = await asyncio.wait_for(check_fn(), timeout=10.0)
            if result.ok and not result.warning:
                msg = f"  \u2705 {name}"
                if args.verbose and result.message:
                    msg += f": {result.message}"
                print(msg)
                passed += 1
            elif result.warning:
                print(f"  \u26a0\ufe0f  {name}: {result.message}")
                warnings += 1
            else:
                print(f"  \u274c {name}: {result.message}")
                failed += 1
        except asyncio.TimeoutError:
            print(f"  \u274c {name}: TIMEOUT (>10s)")
            failed += 1
        except Exception as exc:
            print(f"  \u274c {name}: EXCEPTION \u2014 {exc}")
            if args.verbose:
                traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"  Results: {passed} passed, {warnings} warnings, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summa Vision pre-launch readiness check"
    )
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Skip actual email send test",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output for passing checks",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(run_all_checks(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
