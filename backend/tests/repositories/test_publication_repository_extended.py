"""Tests for the new PublicationRepository methods (Editor + Gallery).

Covers:
* ``create_full`` — visual_config dict is JSON-serialised on the way in.
* ``update_fields`` — partial update preserves untouched fields.
* ``update_fields`` — visual_config Pydantic model is serialised.
* ``publish`` — sets status to PUBLISHED and stamps published_at.
* ``unpublish`` — reverts status to DRAFT.
* ``get_by_id`` — returns ``None`` for unknown IDs.
* ``list_by_status`` — filters by lifecycle status.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.publication import PublicationStatus
from src.repositories.publication_repository import PublicationRepository
from src.schemas.publication import VisualConfig


_VISUAL_DICT = {
    "layout": "bar_editorial",
    "palette": "energy",
    "background": "gradient_midnight",
    "size": "twitter",
    "custom_primary": None,
    "branding": {
        "show_top_accent": True,
        "show_corner_mark": False,
        "accent_color": "#FB7185",
    },
}


@pytest.mark.asyncio
class TestCreateFull:
    """``PublicationRepository.create_full``."""

    async def test_create_full_with_visual_config_dict(
        self, db_session: AsyncSession
    ) -> None:
        """A dict ``visual_config`` should be persisted as a JSON string."""
        repo = PublicationRepository(db_session)
        data = {
            "headline": "Inflation cools",
            "chart_type": "line",
            "eyebrow": "STATCAN · CPI",
            "description": "CPI fell to 2.1% YoY.",
            "source_text": "Source: Statistics Canada",
            "footnote": "Year over year change.",
            "visual_config": _VISUAL_DICT,
            "virality_score": 0.7,
        }

        pub = await repo.create_full(data)
        await db_session.commit()

        assert pub.id is not None
        assert pub.headline == "Inflation cools"
        assert pub.status == PublicationStatus.DRAFT
        assert pub.visual_config is not None
        # The dict was serialised to a JSON string.
        assert isinstance(pub.visual_config, str)
        assert json.loads(pub.visual_config) == _VISUAL_DICT

    async def test_create_full_without_visual_config(
        self, db_session: AsyncSession
    ) -> None:
        """``visual_config`` is optional — None remains None."""
        repo = PublicationRepository(db_session)
        pub = await repo.create_full(
            {"headline": "No visual", "chart_type": "bar"}
        )
        await db_session.commit()
        assert pub.visual_config is None
        assert pub.status == PublicationStatus.DRAFT


@pytest.mark.asyncio
class TestUpdateFields:
    """``PublicationRepository.update_fields``."""

    async def test_partial_update_only_changes_provided_fields(
        self, db_session: AsyncSession
    ) -> None:
        """A patch with one field should leave the rest untouched.

        PATCH contract (see :meth:`PublicationRepository.update_fields`):
        only keys *present* in the dict are applied; omitted keys are
        left alone. The router drives this via
        ``PublicationUpdate.model_dump(exclude_unset=True)`` — so omitted
        JSON fields never appear in the dict passed here.
        """
        repo = PublicationRepository(db_session)
        pub = await repo.create_full(
            {
                "headline": "Original",
                "chart_type": "bar",
                "description": "original description",
            }
        )
        await db_session.commit()

        updated = await repo.update_fields(pub.id, {"headline": "Patched"})
        await db_session.commit()

        assert updated is not None
        assert updated.headline == "Patched"
        # chart_type not in patch — must persist (omitted → unchanged)
        assert updated.chart_type == "bar"
        # description not in patch — must persist
        assert updated.description == "original description"

    async def test_explicit_none_clears_nullable_editorial_field(
        self, db_session: AsyncSession
    ) -> None:
        """An explicit ``None`` in the patch dict clears the column.

        Verifies the PATCH-semantics fix: the router's
        ``model_dump(exclude_unset=True)`` produces ``{"footnote": None}``
        when the client sends ``{"footnote": null}``, and that dict must
        actually clear the database column.
        """
        repo = PublicationRepository(db_session)
        pub = await repo.create_full(
            {
                "headline": "Clearable",
                "chart_type": "bar",
                "footnote": "Seasonally adjusted",
                "eyebrow": "STATCAN",
                "description": "desc",
            }
        )
        await db_session.commit()
        assert pub.footnote == "Seasonally adjusted"

        # Explicit None clears only the fields listed in the dict.
        updated = await repo.update_fields(
            pub.id, {"footnote": None, "eyebrow": None}
        )
        await db_session.commit()

        assert updated is not None
        assert updated.footnote is None
        assert updated.eyebrow is None
        # Untouched key remains
        assert updated.description == "desc"

    async def test_update_with_visual_config_object(
        self, db_session: AsyncSession
    ) -> None:
        """A Pydantic ``VisualConfig`` should be serialised to JSON."""
        repo = PublicationRepository(db_session)
        pub = await repo.create_full(
            {"headline": "Vc test", "chart_type": "bar"}
        )
        await db_session.commit()

        vc = VisualConfig(
            layout="comparison",
            palette="society",
            background="topo",
            size="linkedin",
        )
        updated = await repo.update_fields(pub.id, {"visual_config": vc})
        await db_session.commit()

        assert updated is not None
        assert updated.visual_config is not None
        assert isinstance(updated.visual_config, str)
        parsed = json.loads(updated.visual_config)
        assert parsed["layout"] == "comparison"
        assert parsed["palette"] == "society"
        assert parsed["background"] == "topo"
        assert parsed["size"] == "linkedin"

    async def test_update_returns_none_when_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """Updating a non-existent ID must return ``None``."""
        repo = PublicationRepository(db_session)
        result = await repo.update_fields(999_999, {"headline": "ghost"})
        assert result is None


@pytest.mark.asyncio
class TestPublishUnpublish:
    """``publish`` / ``unpublish`` lifecycle transitions."""

    async def test_publish_sets_status_and_published_at(
        self, db_session: AsyncSession
    ) -> None:
        """publish() should set status=PUBLISHED and stamp published_at."""
        repo = PublicationRepository(db_session)
        pub = await repo.create_full(
            {"headline": "To publish", "chart_type": "bar"}
        )
        await db_session.commit()
        assert pub.status == PublicationStatus.DRAFT
        assert pub.published_at is None

        published = await repo.publish(pub.id)
        await db_session.commit()

        assert published is not None
        assert published.status == PublicationStatus.PUBLISHED
        assert published.published_at is not None

    async def test_unpublish_reverts_to_draft(
        self, db_session: AsyncSession
    ) -> None:
        """unpublish() should flip status back to DRAFT."""
        repo = PublicationRepository(db_session)
        pub = await repo.create_full(
            {"headline": "Round trip", "chart_type": "bar"}
        )
        await db_session.commit()
        await repo.publish(pub.id)
        await db_session.commit()

        reverted = await repo.unpublish(pub.id)
        await db_session.commit()

        assert reverted is not None
        assert reverted.status == PublicationStatus.DRAFT

    async def test_publish_returns_none_when_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """publish() with unknown ID returns ``None``."""
        repo = PublicationRepository(db_session)
        assert await repo.publish(999_999) is None

    async def test_unpublish_returns_none_when_not_found(
        self, db_session: AsyncSession
    ) -> None:
        """unpublish() with unknown ID returns ``None``."""
        repo = PublicationRepository(db_session)
        assert await repo.unpublish(999_999) is None


@pytest.mark.asyncio
class TestGetByIdAndListing:
    """``get_by_id`` and ``list_by_status``."""

    async def test_get_by_id_unknown_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        """get_by_id() with unknown ID returns ``None`` (no exception)."""
        repo = PublicationRepository(db_session)
        assert await repo.get_by_id(999_999) is None

    async def test_list_by_status_filters_drafts(
        self, db_session: AsyncSession
    ) -> None:
        """``status_filter=DRAFT`` returns only drafts."""
        repo = PublicationRepository(db_session)
        await repo.create_full({"headline": "draft 1", "chart_type": "bar"})
        await repo.create_full({"headline": "draft 2", "chart_type": "bar"})
        pub3 = await repo.create_full(
            {"headline": "to be published", "chart_type": "bar"}
        )
        await db_session.commit()
        await repo.publish(pub3.id)
        await db_session.commit()

        drafts = await repo.list_by_status(
            status_filter=PublicationStatus.DRAFT, limit=50, offset=0
        )
        published = await repo.list_by_status(
            status_filter=PublicationStatus.PUBLISHED, limit=50, offset=0
        )
        all_pubs = await repo.list_by_status(
            status_filter=None, limit=50, offset=0
        )
        assert len(drafts) == 2
        assert len(published) == 1
        assert len(all_pubs) == 3
