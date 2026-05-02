"""Phase 3.1a: SemanticMappingRepository tests."""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.schemas.semantic_mapping import (
    SemanticMappingConfig,
    SemanticMappingCreate,
    SemanticMappingUpdate,
)


def _make_create_payload(
    cube_id: str = "18-10-0004",
    product_id: int = 18100004,
    semantic_key: str = "test.key",
    is_active: bool = True,
) -> SemanticMappingCreate:
    return SemanticMappingCreate(
        cube_id=cube_id,
        product_id=product_id,
        semantic_key=semantic_key,
        label="Test mapping",
        config=SemanticMappingConfig(
            dimension_filters={
                "Geography": "Canada",
                "Products": "All-items",
            },
            measure="Value",
            unit="index",
            frequency="monthly",
        ),
        is_active=is_active,
    )


class TestSemanticMappingRepository:
    async def test_create_persists_all_fields(self, db_session):
        repo = SemanticMappingRepository(db_session)
        payload = _make_create_payload()

        mapping = await repo.create(payload, updated_by="test")
        await db_session.commit()

        assert mapping.id is not None
        assert mapping.cube_id == "18-10-0004"
        assert mapping.semantic_key == "test.key"
        assert mapping.config["measure"] == "Value"
        assert mapping.config["frequency"] == "monthly"
        assert mapping.is_active is True
        assert mapping.version == 1
        assert mapping.updated_by == "test"

    async def test_get_by_id(self, db_session):
        repo = SemanticMappingRepository(db_session)
        created = await repo.create(_make_create_payload())
        await db_session.commit()

        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_by_key(self, db_session):
        repo = SemanticMappingRepository(db_session)
        await repo.create(_make_create_payload())
        await db_session.commit()

        fetched = await repo.get_by_key("18-10-0004", "test.key")
        assert fetched is not None
        assert fetched.semantic_key == "test.key"

        missing = await repo.get_by_key("18-10-0004", "nonexistent")
        assert missing is None

    async def test_get_active_for_cube_filters_inactive(self, db_session):
        repo = SemanticMappingRepository(db_session)
        await repo.create(_make_create_payload(semantic_key="active.key"))
        await repo.create(
            _make_create_payload(semantic_key="inactive.key", is_active=False)
        )
        await db_session.commit()

        results = await repo.get_active_for_cube("18-10-0004")
        keys = {m.semantic_key for m in results}
        assert "active.key" in keys
        assert "inactive.key" not in keys

    async def test_get_active_for_cube_orders_by_label(self, db_session):
        repo = SemanticMappingRepository(db_session)
        # Create out of order
        for key, label in [("z.first", "Zebra"), ("a.second", "Alpha")]:
            payload = _make_create_payload(semantic_key=key)
            payload.label = label
            await repo.create(payload)
        await db_session.commit()

        results = list(await repo.get_active_for_cube("18-10-0004"))
        assert results[0].label == "Alpha"
        assert results[1].label == "Zebra"

    async def test_unique_constraint_on_cube_key(self, db_session):
        repo = SemanticMappingRepository(db_session)
        await repo.create(_make_create_payload())
        await db_session.commit()

        with pytest.raises(IntegrityError):
            await repo.create(_make_create_payload())  # same (cube_id, semantic_key)
            await db_session.commit()

    async def test_version_auto_increments_on_update(self, db_session):
        repo = SemanticMappingRepository(db_session)
        mapping = await repo.create(_make_create_payload())
        await db_session.commit()
        assert mapping.version == 1

        await repo.update(
            mapping,
            SemanticMappingUpdate(label="Updated label"),
            updated_by="test",
        )
        await db_session.commit()
        assert mapping.version == 2

        await repo.update(
            mapping,
            SemanticMappingUpdate(description="new description"),
        )
        await db_session.commit()
        assert mapping.version == 3

    async def test_upsert_by_key_creates_when_absent(self, db_session):
        repo = SemanticMappingRepository(db_session)
        mapping, was_created = await repo.upsert_by_key(_make_create_payload())
        await db_session.commit()
        assert was_created is True
        assert mapping.version == 1

    async def test_upsert_by_key_updates_when_present(self, db_session):
        repo = SemanticMappingRepository(db_session)
        first = await repo.create(_make_create_payload())
        await db_session.commit()
        first_id = first.id

        # Same key, different label
        second_payload = _make_create_payload()
        second_payload.label = "Different label"
        second, was_created = await repo.upsert_by_key(second_payload)
        await db_session.commit()

        assert was_created is False
        assert second.id == first_id
        assert second.label == "Different label"
        assert second.version == 2  # bumped via event listener

    async def test_update_partial_only_changes_supplied_fields(self, db_session):
        repo = SemanticMappingRepository(db_session)
        mapping = await repo.create(_make_create_payload())
        original_label = mapping.label
        await db_session.commit()

        # Only update description
        await repo.update(mapping, SemanticMappingUpdate(description="new desc"))
        await db_session.commit()

        assert mapping.label == original_label  # unchanged
        assert mapping.description == "new desc"

    async def test_upsert_by_key_same_payload_does_not_increment_version(
        self, db_session
    ):
        """Phase 3.1a contract: re-seeding identical YAML must not bump version.

        Otherwise before_update event listener would mark all existing
        snapshots stale on every CLI seed run.
        """
        repo = SemanticMappingRepository(db_session)
        payload = _make_create_payload()

        first, was_created = await repo.upsert_by_key(payload)
        await db_session.commit()
        assert was_created is True
        assert first.version == 1

        second, was_created = await repo.upsert_by_key(payload)
        await db_session.commit()
        assert was_created is False
        assert second.id == first.id
        assert second.version == 1  # NOT bumped — payload unchanged

    async def test_upsert_by_key_changed_payload_increments_version(
        self, db_session
    ):
        """Counterpart: actual changes DO bump version."""
        repo = SemanticMappingRepository(db_session)
        payload = _make_create_payload()

        first, _ = await repo.upsert_by_key(payload)
        await db_session.commit()
        assert first.version == 1

        # Modify label
        payload.label = "Different label"
        second, was_created = await repo.upsert_by_key(payload)
        await db_session.commit()
        assert was_created is False
        assert second.version == 2  # bumped because label changed

    async def test_update_can_clear_description_with_explicit_null(
        self, db_session
    ):
        """3.1b admin UI must be able to clear nullable fields via PATCH."""
        repo = SemanticMappingRepository(db_session)
        payload = _make_create_payload()
        payload.description = "initial description"
        mapping = await repo.create(payload)
        await db_session.commit()
        assert mapping.description == "initial description"

        # Explicit null clears the field
        await repo.update(
            mapping,
            SemanticMappingUpdate(description=None),
        )
        await db_session.commit()
        assert mapping.description is None

    async def test_update_omitted_field_unchanged(self, db_session):
        """PATCH semantics: fields not in payload stay as-is."""
        repo = SemanticMappingRepository(db_session)
        payload = _make_create_payload()
        payload.description = "keep me"
        mapping = await repo.create(payload)
        await db_session.commit()

        # Update only label — description must remain
        await repo.update(
            mapping,
            SemanticMappingUpdate(label="new label"),
        )
        await db_session.commit()
        assert mapping.label == "new label"
        assert mapping.description == "keep me"  # untouched
