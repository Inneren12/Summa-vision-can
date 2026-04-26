"""Clone use-case for Publication."""
from __future__ import annotations

import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.publication import Publication, PublicationStatus
from src.repositories.publication_repository import PublicationRepository
from src.services.publications.exceptions import (
    PublicationCloneNotAllowedError,
    PublicationNotFoundError,
)
from src.services.publications.lineage import (
    compute_config_hash,
    derive_size_from_visual_config,
)

_COPY_PREFIX = "Copy of "
_HASH_SLICE = 16
_MAX_CLONE_VERSION_RETRIES = 3


async def clone_publication(*, session: AsyncSession, source_id: int) -> Publication:
    """Clone a published publication into a new draft."""
    repo = PublicationRepository(session)

    source = await repo.get_by_id(source_id)
    if source is None:
        raise PublicationNotFoundError()

    if source.status != PublicationStatus.PUBLISHED:
        status_val = source.status.value if hasattr(source.status, "value") else str(source.status)
        raise PublicationCloneNotAllowedError(
            publication_id=source_id,
            current_status=status_val,
        )

    new_headline = source.headline if source.headline.startswith(_COPY_PREFIX) else f"{_COPY_PREFIX}{source.headline}"

    size = derive_size_from_visual_config(source.visual_config)
    new_config_hash = compute_config_hash(
        chart_type=source.chart_type,
        size=size,
        title=new_headline,
    )[:_HASH_SLICE]

    fresh_review_json = json.dumps(
        {"workflow": "draft", "history": [], "comments": []},
    )

    last_exc: IntegrityError | None = None
    for attempt in range(_MAX_CLONE_VERSION_RETRIES):
        if source.source_product_id is None:
            new_version = 1
        else:
            latest = await repo.get_latest_version(source.source_product_id, new_config_hash)
            new_version = (latest or 0) + 1
        try:
            clone = await repo.create_clone(
                source=source,
                new_headline=new_headline,
                new_config_hash=new_config_hash,
                new_version=new_version,
                fresh_review_json=fresh_review_json,
            )
            await session.commit()
            return clone
        except IntegrityError as exc:
            await session.rollback()
            last_exc = exc
            if attempt == _MAX_CLONE_VERSION_RETRIES - 1:
                raise
            continue

    assert last_exc is not None
    raise last_exc
