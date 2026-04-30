"""Repository-level tests for slug wiring (Phase 2.2.0.5)."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.publication_repository import PublicationRepository
from src.services.publications.lineage import generate_lineage_key
from tests.conftest import make_publication


@pytest.mark.asyncio
class TestGetExistingSlugs:
    async def test_empty_db(self, db_session: AsyncSession) -> None:
        repo = PublicationRepository(db_session)
        slugs = await repo._get_existing_slugs()
        assert slugs == set()

    async def test_returns_all_non_null_slugs(
        self, db_session: AsyncSession
    ) -> None:
        for i, slug in enumerate(["alpha", "beta", "gamma"]):
            db_session.add(
                make_publication(slug=slug, headline=f"Pub {i}")
            )
        await db_session.flush()

        repo = PublicationRepository(db_session)
        slugs = await repo._get_existing_slugs()
        assert {"alpha", "beta", "gamma"}.issubset(slugs)


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
        self, db_session: AsyncSession
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
class TestCreateCloneAssignsFreshSlug:
    async def test_fresh_slug_not_inherited_from_source(
        self, db_session: AsyncSession
    ) -> None:
        source = make_publication(
            slug="source-slug", headline="Source"
        )
        db_session.add(source)
        await db_session.flush()

        repo = PublicationRepository(db_session)
        clone = await repo.create_clone(
            source=source,
            new_headline="Copy of Source",
            new_config_hash="hash",
            new_version=1,
            fresh_review_json="{}",
            lineage_key=source.lineage_key,
        )
        # Clone gets a fresh slug from the new headline,
        # not the source's slug.
        assert clone.slug != source.slug
        assert clone.slug == "copy-of-source"
