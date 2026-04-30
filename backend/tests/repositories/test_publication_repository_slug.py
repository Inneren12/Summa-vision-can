"""Repository-level tests for slug wiring (Phase 2.2.0.5).

Uses the ``make_publication`` pytest fixture from ``tests/conftest.py``
(injected via DI rather than imported) — see Chunk 5 review fix P2.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.publication_repository import PublicationRepository
from src.services.publications.lineage import generate_lineage_key


@pytest.mark.asyncio
class TestGetExistingSlugs:
    async def test_empty_db(self, db_session: AsyncSession) -> None:
        repo = PublicationRepository(db_session)
        slugs = await repo._get_existing_slugs()
        assert slugs == set()

    async def test_returns_all_non_null_slugs(
        self, db_session: AsyncSession, make_publication
    ) -> None:
        for i, slug in enumerate(["alpha", "beta", "gamma"]):
            db_session.add(
                make_publication(slug=slug, headline=f"Pub {i}")
            )
        await db_session.flush()

        repo = PublicationRepository(db_session)
        slugs = await repo._get_existing_slugs()
        assert slugs == {"alpha", "beta", "gamma"}


@pytest.mark.asyncio
class TestCreateFullAssignsSlug:
    async def test_assigns_slug_from_headline(
        self, db_session: AsyncSession
    ) -> None:
        repo = PublicationRepository(db_session)
        pub = await repo.create_full(
            {
                "headline": "Test Article",
                "chart_type": "bar",
                "lineage_key": generate_lineage_key(),
            }
        )
        assert pub.slug == "test-article"

    async def test_collision_assigns_dash_2(
        self, db_session: AsyncSession, make_publication
    ) -> None:
        # Pre-seed a publication with slug "canada-gdp".
        db_session.add(
            make_publication(slug="canada-gdp", headline="Canada GDP seed")
        )
        await db_session.flush()

        repo = PublicationRepository(db_session)
        pub = await repo.create_full(
            {
                "headline": "Canada GDP",
                "chart_type": "line",
                "lineage_key": generate_lineage_key(),
            }
        )
        assert pub.slug == "canada-gdp-2"

    async def test_caller_provided_slug_is_overridden(
        self, db_session: AsyncSession
    ) -> None:
        repo = PublicationRepository(db_session)
        pub = await repo.create_full(
            {
                "headline": "Test Article",
                "slug": "evil-attacker-slug",  # backend must ignore
                "chart_type": "bar",
                "lineage_key": generate_lineage_key(),
            }
        )
        assert pub.slug == "test-article"


@pytest.mark.asyncio
class TestCreateAssignsSlug:
    async def test_create_assigns_slug_from_headline(
        self, db_session: AsyncSession
    ) -> None:
        repo = PublicationRepository(db_session)
        pub = await repo.create(
            headline="Test DRAFT Article",
            chart_type="bar",
            lineage_key=generate_lineage_key(),
        )
        assert pub.slug == "test-draft-article"

    async def test_create_collision_assigns_dash_2(
        self, db_session: AsyncSession, make_publication
    ) -> None:
        db_session.add(
            make_publication(slug="canada-gdp", headline="Pre-existing")
        )
        await db_session.flush()

        repo = PublicationRepository(db_session)
        pub = await repo.create(
            headline="Canada GDP",
            chart_type="line",
            lineage_key=generate_lineage_key(),
        )
        assert pub.slug == "canada-gdp-2"


@pytest.mark.asyncio
class TestCreatePublishedAssignsSlug:
    async def test_create_published_assigns_slug(
        self, db_session: AsyncSession
    ) -> None:
        repo = PublicationRepository(db_session)
        pub = await repo.create_published(
            headline="Q3 Report",
            chart_type="bar",
            s3_key_lowres="lowres/q3.png",
            s3_key_highres="highres/q3.png",
            source_product_id=None,
            version=1,
            config_hash="cfg-hash",
            content_hash="content-hash",
            lineage_key=generate_lineage_key(),
        )
        assert pub.slug == "q3-report"

    async def test_create_published_slug_stable_across_retries(
        self, db_session: AsyncSession, monkeypatch
    ) -> None:
        """Round-5 fix: slug is computed once, before the 3-attempt retry
        loop in ``create_published``. Even if the first INSERT fails with
        ``IntegrityError`` (e.g. on ``(source_product_id, version,
        config_hash)`` collision triggering version+attempt bump), the
        slug stamped on the saved row must equal the slug computed in
        attempt 0 — collision suffix is NOT recomputed per attempt.
        """
        repo = PublicationRepository(db_session)

        real_flush = db_session.flush
        calls = {"n": 0}

        async def flaky_flush(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                # Simulate a UNIQUE constraint violation on the first
                # attempt; SQLAlchemy wraps the underlying DBAPI error
                # in IntegrityError.
                raise IntegrityError("stmt", {}, Exception("dup"))
            return await real_flush(*args, **kwargs)

        monkeypatch.setattr(db_session, "flush", flaky_flush)

        pub = await repo.create_published(
            headline="Stable Slug",
            chart_type="bar",
            s3_key_lowres="lowres/k.png",
            s3_key_highres="highres/k.png",
            source_product_id=None,
            version=1,
            config_hash="cfg-hash",
            content_hash="content-hash",
            lineage_key=generate_lineage_key(),
        )
        assert calls["n"] >= 2  # retry actually fired
        # Slug is the bare slugified headline — no "-2" suffix tacked on
        # by a per-attempt re-computation.
        assert pub.slug == "stable-slug"


@pytest.mark.asyncio
class TestCreateCloneAssignsFreshSlug:
    async def test_clone_slug_built_from_new_headline_not_source(
        self, db_session: AsyncSession, make_publication
    ) -> None:
        """Clone slug derives from the final clone headline (``new_headline``),
        NOT from ``source.headline``. Round-3 refactor locked this contract
        (see ``derive_clone_slug`` docstring).

        The "Different Topic Entirely" vs "Old Source Article" gap makes
        it impossible for a buggy ``derive_clone_slug(source.headline)``
        call to accidentally pass.
        """
        source = make_publication(
            slug="old-source-slug", headline="Old Source Article"
        )
        db_session.add(source)
        await db_session.flush()

        repo = PublicationRepository(db_session)
        clone = await repo.create_clone(
            source=source,
            new_headline="Different Topic Entirely",
            new_config_hash="hash",
            new_version=1,
            fresh_review_json="{}",
            lineage_key=source.lineage_key,
        )
        assert clone.slug == "different-topic-entirely"
        assert "old-source" not in clone.slug
        assert clone.slug != source.slug
