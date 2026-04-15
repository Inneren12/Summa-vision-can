"""Tests for the extended Publication model (Editor + Gallery extension).

Covers:
* Round-trip persistence of the new editorial fields.
* JSON round-trip of ``visual_config`` (dict → JSON string → dict).
* Auto-population of ``updated_at`` on update.
* Manual stamping of ``published_at``.
* Backward compatibility — pre-existing rows don't break and all new
  fields are ``None`` when not set.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.publication import Publication, PublicationStatus


_VISUAL_CONFIG = {
    "layout": "single_stat",
    "palette": "housing",
    "background": "gradient_warm",
    "size": "instagram",
    "custom_primary": "#22D3EE",
    "branding": {
        "show_top_accent": True,
        "show_corner_mark": True,
        "accent_color": "#FBBF24",
    },
}


@pytest.mark.asyncio
class TestPublicationExtended:
    """Test suite for the new editorial / visual_config fields."""

    async def test_round_trip_all_fields(self, db_session: AsyncSession) -> None:
        """Every new field must persist and read back unchanged."""
        pub = Publication(
            headline="Housing starts hit record high",
            chart_type="bar",
            eyebrow="STATISTICS CANADA · TABLE 18-10-0004",
            description="A short blurb for the gallery card.",
            source_text="Source: Statistics Canada, Table 18-10-0004-01",
            footnote="Methodology note: seasonally adjusted.",
            visual_config=json.dumps(_VISUAL_CONFIG),
            virality_score=0.85,
        )
        db_session.add(pub)
        await db_session.flush()
        await db_session.commit()

        # Fresh query — confirm the values come back from the DB
        result = await db_session.execute(
            select(Publication).where(Publication.id == pub.id)
        )
        loaded = result.scalar_one()
        assert loaded.headline == "Housing starts hit record high"
        assert loaded.eyebrow == "STATISTICS CANADA · TABLE 18-10-0004"
        assert loaded.description == "A short blurb for the gallery card."
        assert loaded.source_text == "Source: Statistics Canada, Table 18-10-0004-01"
        assert loaded.footnote == "Methodology note: seasonally adjusted."
        assert loaded.visual_config is not None
        assert loaded.virality_score == pytest.approx(0.85)

    async def test_visual_config_json_round_trip(
        self, db_session: AsyncSession
    ) -> None:
        """``visual_config`` is stored as JSON; round-trip must match dict."""
        pub = Publication(
            headline="Visual config test",
            chart_type="bar",
            visual_config=json.dumps(_VISUAL_CONFIG),
        )
        db_session.add(pub)
        await db_session.flush()
        await db_session.commit()

        loaded = await db_session.get(Publication, pub.id)
        assert loaded is not None
        assert loaded.visual_config is not None
        parsed = json.loads(loaded.visual_config)
        assert parsed == _VISUAL_CONFIG

    async def test_updated_at_set_on_update(
        self, db_session: AsyncSession
    ) -> None:
        """Modifying a record must populate ``updated_at`` automatically."""
        pub = Publication(headline="Initial", chart_type="bar")
        db_session.add(pub)
        await db_session.flush()
        # Initially updated_at is None
        assert pub.updated_at is None

        pub_id = pub.id

        # Mutate via UPDATE so SQLAlchemy's onupdate callback fires.
        from sqlalchemy import update
        await asyncio.sleep(0.01)
        await db_session.execute(
            update(Publication)
            .where(Publication.id == pub_id)
            .values(headline="Updated headline")
        )
        await db_session.flush()
        await db_session.commit()

        # Re-query in a fresh statement so we pick up the new updated_at.
        db_session.expire_all()
        result = await db_session.execute(
            select(Publication).where(Publication.id == pub_id)
        )
        loaded = result.scalar_one()
        assert loaded.headline == "Updated headline"
        assert loaded.updated_at is not None

    async def test_published_at_set_when_publishing(
        self, db_session: AsyncSession
    ) -> None:
        """Setting ``published_at`` manually persists alongside status."""
        pub = Publication(headline="Pending", chart_type="bar")
        db_session.add(pub)
        await db_session.flush()
        await db_session.commit()
        assert pub.published_at is None

        pub.status = PublicationStatus.PUBLISHED
        pub.published_at = datetime.now(timezone.utc)
        await db_session.flush()
        await db_session.commit()

        loaded = await db_session.get(Publication, pub.id)
        assert loaded is not None
        assert loaded.status == PublicationStatus.PUBLISHED
        assert loaded.published_at is not None

    async def test_defaults_for_legacy_rows(
        self, db_session: AsyncSession
    ) -> None:
        """A row created without the new fields must default them to None."""
        pub = Publication(headline="Legacy", chart_type="bar")
        db_session.add(pub)
        await db_session.flush()
        await db_session.commit()

        loaded = await db_session.get(Publication, pub.id)
        assert loaded is not None
        assert loaded.eyebrow is None
        assert loaded.description is None
        assert loaded.source_text is None
        assert loaded.footnote is None
        assert loaded.visual_config is None
        assert loaded.updated_at is None
        assert loaded.published_at is None
