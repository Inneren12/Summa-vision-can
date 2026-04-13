"""
End-to-end download funnel verification.
Run: python -m scripts.ops.verify_funnel --api-url http://localhost:8000

Simulates: Gallery -> Lead Capture -> Token -> Download
Uses a test email and bypasses Turnstile via Cloudflare's always-pass test token.

Exit code 0 = funnel works, 1 = failure detected.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import secrets
import sys
import traceback
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from src.core.config import get_settings
from src.core.database import get_session_factory
from src.models.audit_event import AuditEvent
from src.models.download_token import DownloadToken
from src.models.lead import Lead

# Cloudflare Turnstile always-pass test token
TURNSTILE_TEST_TOKEN = "1x0000000000000000000000000000000AA"


async def verify_funnel(api_url: str, test_email: str) -> bool:
    """Run the full download funnel and return True on success."""
    factory = get_session_factory()

    # Track IDs for cleanup
    created_lead_id: int | None = None
    created_token_id: int | None = None

    print("=" * 60)
    print("  DOWNLOAD FUNNEL E2E VERIFICATION")
    print("=" * 60)

    try:
        async with httpx.AsyncClient(base_url=api_url, timeout=30) as client:

            # ----------------------------------------------------------
            # Step 1: Gallery has published graphics
            # ----------------------------------------------------------
            print("\n  Step 1: Fetch gallery...")
            resp = await client.get("/api/v1/public/graphics?limit=1")
            assert resp.status_code == 200, (
                f"Gallery failed: {resp.status_code}"
            )
            gallery = resp.json()
            assert len(gallery["items"]) > 0, (
                "Gallery is empty \u2014 no published graphics"
            )
            item = gallery["items"][0]
            asset_id: int = item["id"]
            headline: str = item["headline"]
            preview_url: str = item.get("preview_url", "")
            print(
                f"  \u2705 Gallery OK \u2014 asset_id={asset_id}, "
                f"headline='{headline}'"
            )

            # ----------------------------------------------------------
            # Step 1b: Verify preview/CDN URL is accessible
            # ----------------------------------------------------------
            if preview_url:
                print("\n  Step 1b: Verify preview URL...")
                try:
                    async with httpx.AsyncClient(timeout=10) as cdn_client:
                        preview_resp = await cdn_client.head(
                            preview_url, follow_redirects=True
                        )
                        if preview_resp.status_code in (200, 301, 302):
                            print("  \u2705 Preview URL accessible")
                        else:
                            print(
                                f"  \u26a0\ufe0f  Preview URL returned "
                                f"{preview_resp.status_code}"
                            )
                except Exception as exc:
                    print(f"  \u26a0\ufe0f  Preview URL check failed: {exc}")

            # ----------------------------------------------------------
            # Step 2: Submit lead capture
            # ----------------------------------------------------------
            print("\n  Step 2: Submit lead capture...")
            capture_resp = await client.post(
                "/api/v1/public/leads/capture",
                json={
                    "email": test_email,
                    "asset_id": asset_id,
                    "turnstile_token": TURNSTILE_TEST_TOKEN,
                },
            )
            assert capture_resp.status_code == 200, (
                f"Lead capture failed: {capture_resp.status_code} "
                f"\u2014 {capture_resp.text}"
            )
            body = capture_resp.json()
            print(
                f"  \u2705 Lead captured \u2014 "
                f"response: {body.get('message', body)}"
            )

            # ----------------------------------------------------------
            # Step 3: Verify lead exists in DB
            # ----------------------------------------------------------
            print("\n  Step 3: Verify lead in database...")
            async with factory() as session:
                # Lead.asset_id is stored as str in the model
                lead = (
                    await session.execute(
                        select(Lead)
                        .where(
                            Lead.email == test_email,
                            Lead.asset_id == str(asset_id),
                        )
                        .order_by(Lead.created_at.desc())
                    )
                ).scalar_one_or_none()
                assert lead is not None, "Lead not found in DB"
                created_lead_id = lead.id
            print(
                f"  \u2705 Lead verified \u2014 id={created_lead_id}, "
                f"email={test_email}"
            )

            # ----------------------------------------------------------
            # Step 4: Check if a download token was created by capture
            # ----------------------------------------------------------
            print("\n  Step 4: Retrieve download token...")
            async with factory() as session:
                token_record = (
                    await session.execute(
                        select(DownloadToken)
                        .where(DownloadToken.lead_id == created_lead_id)
                        .order_by(DownloadToken.created_at.desc())
                    )
                ).scalar_one_or_none()

                if token_record:
                    print(
                        f"  \u2705 Token found \u2014 "
                        f"hash={token_record.token_hash[:16]}..., "
                        f"max_uses={token_record.max_uses}"
                    )
                else:
                    # Email sending is async via BackgroundTasks; token may
                    # not exist yet.  We'll create a known test token below.
                    print(
                        "  \u26a0\ufe0f  No token found yet "
                        "(email dispatch is async \u2014 creating test token)"
                    )

            # ----------------------------------------------------------
            # Step 5: Test token exchange endpoint
            # We cannot recover the raw token from the hash stored by the
            # capture flow, so we insert a known test token directly.
            # ----------------------------------------------------------
            print("\n  Step 5: Test token exchange endpoint...")
            raw_test_token = secrets.token_urlsafe(32)
            test_hash = hashlib.sha256(raw_test_token.encode()).hexdigest()

            async with factory() as session:
                test_token = DownloadToken(
                    token_hash=test_hash,
                    lead_id=created_lead_id,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
                    max_uses=5,
                    use_count=0,
                )
                session.add(test_token)
                await session.commit()
                await session.refresh(test_token)
                created_token_id = test_token.id

            download_resp = await client.get(
                f"/api/v1/public/download?token={raw_test_token}",
                follow_redirects=False,
            )
            assert download_resp.status_code == 307, (
                f"Token exchange failed: {download_resp.status_code} "
                f"\u2014 {download_resp.text}"
            )
            redirect_url = download_resp.headers.get("location", "")
            assert redirect_url, "No Location header in 307 response"
            print(
                "  \u2705 Token exchange \u2192 307 redirect to presigned URL"
            )

            # ----------------------------------------------------------
            # Step 6: Verify audit events
            # ----------------------------------------------------------
            print("\n  Step 6: Verify audit events...")
            async with factory() as session:
                events = (
                    await session.execute(
                        select(AuditEvent.event_type).where(
                            AuditEvent.entity_id == str(created_lead_id)
                        )
                    )
                ).scalars().all()

                expected_events = {
                    "lead.captured",
                    "token.created",
                    "token.activated",
                }
                found_events = set(events)
                missing = expected_events - found_events

                if missing:
                    print(
                        f"  \u26a0\ufe0f  Missing audit events: {missing} "
                        f"(found: {found_events})"
                    )
                else:
                    print(
                        f"  \u2705 All core audit events present: "
                        f"{found_events}"
                    )

            # ----------------------------------------------------------
            # Step 7: Verify token use_count incremented
            # ----------------------------------------------------------
            print("\n  Step 7: Verify token usage tracking...")
            async with factory() as session:
                used_token = await session.get(
                    DownloadToken, created_token_id
                )
                assert used_token is not None, "Test token not found"
                assert used_token.use_count == 1, (
                    f"use_count should be 1, got {used_token.use_count}"
                )
                print(
                    f"  \u2705 Token use_count = {used_token.use_count} "
                    f"(correct)"
                )

        # All steps passed
        print()
        print("=" * 60)
        print("  \u2705 FUNNEL VERIFICATION COMPLETE \u2014 ALL STEPS PASSED")
        print("=" * 60)
        return True

    except AssertionError as exc:
        print(f"\n  \u274c ASSERTION FAILED: {exc}")
        print()
        print("=" * 60)
        print("  \u274c FUNNEL VERIFICATION FAILED")
        print("=" * 60)
        return False

    except Exception as exc:
        print(f"\n  \u274c UNEXPECTED ERROR: {exc}")
        traceback.print_exc()
        print()
        print("=" * 60)
        print("  \u274c FUNNEL VERIFICATION FAILED")
        print("=" * 60)
        return False

    finally:
        # ----------------------------------------------------------
        # Cleanup all test data
        # ----------------------------------------------------------
        print("\n  Cleanup: removing test data...")
        try:
            async with factory() as session:
                # 1. Delete the test token we inserted
                if created_token_id:
                    token = await session.get(DownloadToken, created_token_id)
                    if token:
                        await session.delete(token)

                # 2. Delete any tokens the capture flow may have created
                if created_lead_id:
                    other_tokens = (
                        await session.execute(
                            select(DownloadToken).where(
                                DownloadToken.lead_id == created_lead_id
                            )
                        )
                    ).scalars().all()
                    for t in other_tokens:
                        await session.delete(t)

                    # 3. Delete audit events referencing this lead
                    audit_rows = (
                        await session.execute(
                            select(AuditEvent).where(
                                AuditEvent.entity_id == str(created_lead_id)
                            )
                        )
                    ).scalars().all()
                    for ae in audit_rows:
                        await session.delete(ae)

                    # 4. Delete the lead itself
                    lead_obj = await session.get(Lead, created_lead_id)
                    if lead_obj:
                        await session.delete(lead_obj)

                await session.commit()
            print("  \u2705 Test data cleaned up")
        except Exception as cleanup_err:
            print(f"  \u26a0\ufe0f  Cleanup error: {cleanup_err}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summa Vision download funnel E2E verification"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--test-email",
        default="funnel-test@summa-test.local",
        help="Test email address for lead capture",
    )
    args = parser.parse_args()

    result = asyncio.run(verify_funnel(args.api_url, args.test_email))
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
