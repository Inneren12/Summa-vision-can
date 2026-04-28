from __future__ import annotations

import json

import pytest

from src.models.publication import Publication, PublicationStatus
from src.services.publications.clone import clone_publication
from src.services.publications.exceptions import PublicationCloneNotAllowedError, PublicationNotFoundError
from tests.conftest import make_publication


async def _make_source(
    db_session,
    *,
    headline: str = 'Headline',
    status: PublicationStatus = PublicationStatus.PUBLISHED,
    config_hash: str = 'aaaaaaaaaaaaaaaa',
    source_product_id: str | None = 'P1',
    chart_type: str = 'bar',
    eyebrow: str = 'Eyebrow',
    description: str = 'Desc',
    source_text: str = 'Source',
    footnote: str = 'Foot',
    visual_config: str | None = None,
    document_state: str | None = '{"doc":1}',
    review: str | None = None,
    version: int = 1,
) -> Publication:
    src = make_publication(
        headline=headline,
        chart_type=chart_type,
        eyebrow=eyebrow,
        description=description,
        source_text=source_text,
        footnote=footnote,
        visual_config=visual_config or json.dumps({'size': 'instagram'}),
        document_state=document_state,
        review=review or json.dumps({'workflow': 'published', 'history': [], 'comments': []}),
        source_product_id=source_product_id,
        config_hash=config_hash,
        version=version,
        content_hash='bbbbbbbbbbbbbbbb',
        s3_key_lowres='low',
        s3_key_highres='high',
        virality_score=0.8,
        status=status,
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
async def test_clone_resets_document_state_to_none(db_session) -> None:
    """document_state MUST be None on clone to avoid re-publish via hydration."""
    src_doc_state = json.dumps({
        "schemaVersion": 2,
        "templateId": "default",
        "page": {"size": "instagram_1080"},
        "sections": [],
        "blocks": [],
        "review": {"workflow": "published", "history": [], "comments": []},
        "meta": {"history": []},
    })
    src = await _make_source(
        db_session,
        headline='X',
        document_state=src_doc_state,
        status=PublicationStatus.PUBLISHED,
    )
    clone = await clone_publication(session=db_session, source_id=src.id)
    assert clone.document_state is None


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


@pytest.mark.asyncio
async def test_clone_retries_on_version_collision(db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    src = await _make_source(db_session, source_product_id='P-race')

    class FakeRepo:
        def __init__(self, session):
            self.calls = 0
            self._session = session

        async def get_by_id(self, publication_id: int):
            return src

        async def get_latest_version(self, source_product_id: str, config_hash: str):
            return 1 if self.calls == 0 else 2

        async def create_clone(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                from sqlalchemy.exc import IntegrityError
                raise IntegrityError('insert', {}, Exception('collision'))
            clone = make_publication(
                headline='Copy of X',
                chart_type=src.chart_type,
                status=PublicationStatus.DRAFT,
                review=kwargs['fresh_review_json'],
                config_hash=kwargs['new_config_hash'],
                version=kwargs['new_version'],
                cloned_from_publication_id=src.id,
                lineage_key=kwargs['lineage_key'],
            )
            return clone

    from src.services.publications import clone as clone_module

    monkeypatch.setattr(clone_module, 'PublicationRepository', FakeRepo)
    clone = await clone_module.clone_publication(session=db_session, source_id=src.id)
    assert clone.version == 3
