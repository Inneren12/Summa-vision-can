"""Tests for PublicationRepository.

Covers the full CRUD cycle: create, get_published (with pagination),
and update_status.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.publication import PublicationStatus
from src.repositories.publication_repository import PublicationRepository
from src.services.publications.lineage import generate_lineage_key


@pytest.mark.asyncio
class TestPublicationRepository:
    """Test suite for :class:`PublicationRepository`."""

    async def test_create_publication(self, db_session: AsyncSession) -> None:
        """Creating a publication should persist it and assign an id."""
        repo = PublicationRepository(db_session)

        pub = await repo.create(
            headline="Housing starts hit record high",
            chart_type="bar",
            s3_key_lowres="low/key.png",
            s3_key_highres="high/key.png",
            virality_score=0.85,
            lineage_key=generate_lineage_key(),
        )

        assert pub.id is not None
        assert pub.headline == "Housing starts hit record high"
        assert pub.chart_type == "bar"
        assert pub.s3_key_lowres == "low/key.png"
        assert pub.s3_key_highres == "high/key.png"
        assert pub.virality_score == pytest.approx(0.85)
        assert pub.status == PublicationStatus.DRAFT
        assert pub.created_at is not None

    async def test_create_publication_defaults(
        self, db_session: AsyncSession
    ) -> None:
        """Creating with minimal args should use sane defaults."""
        repo = PublicationRepository(db_session)

        pub = await repo.create(
            headline="Minimal pub",
            chart_type="line",
            lineage_key=generate_lineage_key(),
        )

        assert pub.status == PublicationStatus.DRAFT
        assert pub.s3_key_lowres is None
        assert pub.s3_key_highres is None
        assert pub.virality_score is None

    async def test_get_published_returns_only_published(
        self, db_session: AsyncSession
    ) -> None:
        """get_published should return only PUBLISHED items, newest first."""
        repo = PublicationRepository(db_session)

        # Create a mix of DRAFT and PUBLISHED
        await repo.create(
            headline="Draft 1",
            chart_type="bar",
            lineage_key=generate_lineage_key(),
        )
        pub2 = await repo.create(
            headline="Published 1",
            chart_type="line",
            status=PublicationStatus.PUBLISHED,
            lineage_key=generate_lineage_key(),
        )
        pub3 = await repo.create(
            headline="Published 2",
            chart_type="pie",
            status=PublicationStatus.PUBLISHED,
            lineage_key=generate_lineage_key(),
        )
        await repo.create(
            headline="Draft 2",
            chart_type="area",
            lineage_key=generate_lineage_key(),
        )
        await db_session.commit()

        results = await repo.get_published(limit=10, offset=0)

        assert len(results) == 2
        # Newest first
        assert results[0].id == pub3.id
        assert results[1].id == pub2.id

    async def test_get_published_pagination(
        self, db_session: AsyncSession
    ) -> None:
        """get_published should respect limit and offset."""
        repo = PublicationRepository(db_session)

        for i in range(5):
            await repo.create(
                headline=f"Publication {i}",
                chart_type="bar",
                status=PublicationStatus.PUBLISHED,
                lineage_key=generate_lineage_key(),
            )
        await db_session.commit()

        page1 = await repo.get_published(limit=2, offset=0)
        page2 = await repo.get_published(limit=2, offset=2)
        page3 = await repo.get_published(limit=2, offset=4)

        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

    async def test_get_published_empty(
        self, db_session: AsyncSession
    ) -> None:
        """get_published returns empty list when no published records."""
        repo = PublicationRepository(db_session)
        await repo.create(
            headline="Only draft",
            chart_type="bar",
            lineage_key=generate_lineage_key(),
        )
        await db_session.commit()

        results = await repo.get_published(limit=10, offset=0)
        assert results == []

    async def test_update_status(self, db_session: AsyncSession) -> None:
        """update_status should change the publication status."""
        repo = PublicationRepository(db_session)
        pub = await repo.create(
            headline="To publish",
            chart_type="bar",
            lineage_key=generate_lineage_key(),
        )
        await db_session.commit()

        assert pub.status == PublicationStatus.DRAFT

        await repo.update_status(pub.id, PublicationStatus.PUBLISHED)
        await db_session.commit()

        # Re-query to verify
        published = await repo.get_published(limit=10, offset=0)
        assert len(published) == 1
        assert published[0].id == pub.id

    async def test_full_lifecycle(self, db_session: AsyncSession) -> None:
        """Full lifecycle: create → update → query."""
        repo = PublicationRepository(db_session)

        # Create as draft
        pub = await repo.create(
            headline="Full lifecycle test",
            chart_type="infographic",
            virality_score=0.72,
            lineage_key=generate_lineage_key(),
        )
        await db_session.commit()
        assert pub.status == PublicationStatus.DRAFT

        # Initially nothing published
        assert await repo.get_published(limit=10, offset=0) == []

        # Publish it
        await repo.update_status(pub.id, PublicationStatus.PUBLISHED)
        await db_session.commit()

        # Now it shows up
        published = await repo.get_published(limit=10, offset=0)
        assert len(published) == 1
        assert published[0].headline == "Full lifecycle test"

    # -----------------------------------------------------------------
    # Phase 2.2.0 chunk 3c — lineage_key persistence per write-path
    # -----------------------------------------------------------------

    async def test_create_full_persists_lineage_key(
        self, db_session: AsyncSession
    ) -> None:
        """create_full persists the lineage_key supplied via data dict."""
        repo = PublicationRepository(db_session)
        lineage_key = generate_lineage_key()

        pub = await repo.create_full(
            {
                "headline": "Admin create_full",
                "chart_type": "bar",
                "lineage_key": lineage_key,
            }
        )
        await db_session.commit()

        fetched = await repo.get_by_id(pub.id)
        assert fetched is not None
        assert fetched.lineage_key == lineage_key

    async def test_create_clone_persists_lineage_key(
        self, db_session: AsyncSession
    ) -> None:
        """create_clone persists the lineage_key from the inheritance helper."""
        repo = PublicationRepository(db_session)
        source_lineage_key = generate_lineage_key()

        source = await repo.create(
            headline="source",
            chart_type="bar",
            lineage_key=source_lineage_key,
            status=PublicationStatus.PUBLISHED,
        )
        await db_session.commit()

        clone = await repo.create_clone(
            source=source,
            new_headline="Copy of source",
            new_config_hash="abcd" * 4,
            new_version=2,
            fresh_review_json='{"workflow": "draft", "history": [], "comments": []}',
            lineage_key=source_lineage_key,
        )
        await db_session.commit()

        fetched = await repo.get_by_id(clone.id)
        assert fetched is not None
        assert fetched.lineage_key == source_lineage_key

    async def test_create_persists_lineage_key(
        self, db_session: AsyncSession
    ) -> None:
        """The basic create() method persists the supplied lineage_key."""
        repo = PublicationRepository(db_session)
        lineage_key = generate_lineage_key()

        pub = await repo.create(
            headline="basic create",
            chart_type="line",
            lineage_key=lineage_key,
        )
        await db_session.commit()

        fetched = await repo.get_by_id(pub.id)
        assert fetched is not None
        assert fetched.lineage_key == lineage_key

    async def test_create_published_persists_lineage_key(
        self, db_session: AsyncSession
    ) -> None:
        """create_published (versioned write path) persists the lineage_key."""
        repo = PublicationRepository(db_session)
        lineage_key = generate_lineage_key()

        pub = await repo.create_published(
            headline="versioned create",
            chart_type="bar",
            s3_key_lowres="low/k.png",
            s3_key_highres="high/k.png",
            source_product_id="P-versioned",
            version=1,
            config_hash="deadbeefcafebabe",
            content_hash="0123456789abcdef",
            lineage_key=lineage_key,
        )
        await db_session.commit()

        fetched = await repo.get_by_id(pub.id)
        assert fetched is not None
        assert fetched.lineage_key == lineage_key
