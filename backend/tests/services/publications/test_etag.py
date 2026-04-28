"""Unit tests for the pure ETag derivation function (Phase 1.3)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models.publication import Publication, PublicationStatus
from src.services.publications.etag import compute_etag
from tests.conftest import make_publication


def _make_pub(
    *,
    pub_id: int = 42,
    updated_at: datetime | None = None,
    created_at: datetime | None = None,
    config_hash: str | None = "abc123",
) -> Publication:
    """Build an in-memory Publication for ETag tests.

    Avoids hitting the DB — the function under test is pure and only reads
    attributes from the entity, so an unsaved instance is sufficient.
    """
    pub = make_publication(
        headline="H",
        chart_type="bar",
        status=PublicationStatus.DRAFT,
        config_hash=config_hash,
    )
    pub.id = pub_id
    pub.created_at = created_at or datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    pub.updated_at = updated_at
    return pub


def test_compute_etag_deterministic() -> None:
    """Same inputs produce the same ETag (no clock reads, no randomness)."""
    pub_a = _make_pub(
        pub_id=1,
        updated_at=datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc),
        config_hash="hash1",
    )
    pub_b = _make_pub(
        pub_id=1,
        updated_at=datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc),
        config_hash="hash1",
    )
    assert compute_etag(pub_a) == compute_etag(pub_b)


def test_compute_etag_changes_on_updated_at() -> None:
    """Different ``updated_at`` ⇒ different ETag (write must invalidate)."""
    pub_a = _make_pub(
        pub_id=1,
        updated_at=datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc),
    )
    pub_b = _make_pub(
        pub_id=1,
        updated_at=datetime(2026, 4, 27, 12, 0, 1, tzinfo=timezone.utc),
    )
    assert compute_etag(pub_a) != compute_etag(pub_b)


def test_compute_etag_fallback_to_created_at() -> None:
    """``updated_at = None`` falls back to ``created_at`` without crashing.

    Anchor regression test for fresh DRAFT rows that have never been written.
    """
    pub = _make_pub(
        pub_id=1,
        updated_at=None,
        created_at=datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc),
    )
    etag = compute_etag(pub)
    assert etag.startswith('"')
    # Round-trip the same created_at — must match.
    pub_again = _make_pub(
        pub_id=1,
        updated_at=None,
        created_at=datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert compute_etag(pub_again) == etag


def test_compute_etag_null_config_hash() -> None:
    """``config_hash = None`` substitutes ``""`` — never the literal string ``"None"``.

    Anchor regression test against an accidental ``f"{pub.config_hash}"``
    that would inject ``"None"`` into the digest input on null rows.
    """
    pub_null = _make_pub(pub_id=1, config_hash=None)
    pub_empty = _make_pub(pub_id=1, config_hash="")
    assert compute_etag(pub_null) == compute_etag(pub_empty)


def test_compute_etag_uses_pipe_separator() -> None:
    """The pipe ``|`` separator is load-bearing — anchor regression for Q1.

    Built using the same inputs the production function consumes; if anyone
    changes the separator, this test guards against the silent invalidation
    of every cached client ``If-Match`` token.
    """
    import hashlib

    ts = datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc)
    pub = _make_pub(pub_id=42, updated_at=ts, config_hash="cfg")
    expected_raw = f"42|{ts.isoformat()}|cfg"
    expected_digest = hashlib.sha256(expected_raw.encode("utf-8")).hexdigest()[:16]
    assert compute_etag(pub) == f'"{expected_digest}"'


def test_compute_etag_format_is_strong() -> None:
    """ETag is strong per RFC 7232 §2.3 — derived from row metadata, not body."""
    pub = _make_pub()
    etag = compute_etag(pub)
    assert etag.startswith('"')
    assert etag.endswith('"')
    # 16 hex chars between the quotes.
    inner = etag[1:-1]
    assert len(inner) == 16
    assert all(c in "0123456789abcdef" for c in inner)
