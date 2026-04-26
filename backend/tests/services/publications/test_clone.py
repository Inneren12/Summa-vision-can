from __future__ import annotations

import json

import pytest

from src.models.publication import Publication, PublicationStatus
from src.services.publications.clone import clone_publication
from src.services.publications.exceptions import PublicationCloneNotAllowedError, PublicationNotFoundError


async def _make_source(db_session, **overrides) -> Publication:
    src = Publication(
        headline='Headline',
        chart_type='bar',
        eyebrow='Eyebrow',
        description='Desc',
        source_text='Source',
        footnote='Foot',
        visual_config=json.dumps({'size': 'instagram'}),
        document_state='{"doc":1}',
        review=json.dumps({'workflow': 'published', 'history': [], 'comments': []}),
        source_product_id='P1',
        config_hash='aaaaaaaaaaaaaaaa',
        version=1,
        content_hash='bbbbbbbbbbbbbbbb',
        s3_key_lowres='low',
        s3_key_highres='high',
        virality_score=0.8,
        status=PublicationStatus.PUBLISHED,
        **overrides,
    )
    db_session.add(src)
    await db_session.flush()
    await db_session.refresh(src)
    return src


@pytest.mark.asyncio
async def test_clone_published_creates_draft_with_copy_prefix(db_session) -> None:
    src = await _make_source(db_session, headline='X')
    clone = await clone_publication(session=db_session, source_id=src.id)
    assert clone.headline == 'Copy of X'
    assert clone.status == PublicationStatus.DRAFT
    assert clone.cloned_from_publication_id == src.id


@pytest.mark.asyncio
async def test_clone_already_prefixed_does_not_double_prefix(db_session) -> None:
    src = await _make_source(db_session, headline='Copy of X')
    clone = await clone_publication(session=db_session, source_id=src.id)
    assert clone.headline == 'Copy of X'


@pytest.mark.asyncio
async def test_clone_resets_lifecycle_fields(db_session) -> None:
    src = await _make_source(db_session)
    clone = await clone_publication(session=db_session, source_id=src.id)
    assert clone.s3_key_lowres is None
    assert clone.s3_key_highres is None
    assert clone.published_at is None
    assert clone.virality_score is None
    assert clone.content_hash is None


@pytest.mark.asyncio
async def test_clone_copies_content_fields(db_session) -> None:
    src = await _make_source(db_session)
    clone = await clone_publication(session=db_session, source_id=src.id)
    assert clone.eyebrow == src.eyebrow
    assert clone.description == src.description
    assert clone.source_text == src.source_text
    assert clone.footnote == src.footnote
    assert clone.visual_config == src.visual_config
    assert clone.document_state == src.document_state


@pytest.mark.asyncio
async def test_clone_resets_review_to_empty_workflow(db_session) -> None:
    src = await _make_source(db_session)
    clone = await clone_publication(session=db_session, source_id=src.id)
    assert json.loads(clone.review or '{}') == {'workflow': 'draft', 'history': [], 'comments': []}


@pytest.mark.asyncio
async def test_clone_recomputes_config_hash(db_session) -> None:
    src = await _make_source(db_session, config_hash='1234567890abcdef')
    clone = await clone_publication(session=db_session, source_id=src.id)
    assert clone.config_hash != src.config_hash


@pytest.mark.asyncio
async def test_clone_starts_at_version_1_when_lineage_isolated(db_session) -> None:
    src = await _make_source(db_session, source_product_id=None)
    clone = await clone_publication(session=db_session, source_id=src.id)
    assert clone.version == 1


@pytest.mark.asyncio
async def test_clone_increments_version_when_lineage_collides(db_session) -> None:
    src = await _make_source(db_session)
    first = await clone_publication(session=db_session, source_id=src.id)
    second = await clone_publication(session=db_session, source_id=src.id)
    assert first.version == 1
    assert second.version == 2


@pytest.mark.asyncio
async def test_clone_of_draft_raises_not_allowed(db_session) -> None:
    src = await _make_source(db_session, status=PublicationStatus.DRAFT)
    with pytest.raises(PublicationCloneNotAllowedError):
        await clone_publication(session=db_session, source_id=src.id)


@pytest.mark.asyncio
async def test_clone_missing_source_raises_not_found(db_session) -> None:
    with pytest.raises(PublicationNotFoundError):
        await clone_publication(session=db_session, source_id=999999)
