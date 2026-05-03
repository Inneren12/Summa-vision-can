# Phase 3.1d — RECON (snapshot persistence + staleness comparison)

## 1) Locked decisions table

| ID | Decision | Source |
|---|---|---|
| **Q1** | **Snapshot storage:** separate table `publication_block_snapshot`. Inline option dead per §B2 #4 (validator strips unknown block.props keys via `sanitizeBlockProps`). | §F Q1 / §B2 #4 |
| **Q2** | **Snapshot key:** `UNIQUE(publication_id, block_id)`. Semantic context (cube_id, semantic_key, coord, period) stored on the row alongside the snapshot fingerprint. | §F Q2 |
| **Q3** | **Comparator model:** §J ComparatorResult adopted, with **7 reasons** (5 from §J + 2 new): `mapping_version_changed`, `source_hash_changed`, `value_changed`, `missing_state_changed`, `cache_row_stale`, **`compare_failed`**, **`snapshot_missing`**. | §F Q3 + Q3-followup |
| **Q3-severity** | Per-reason severity mapping: `compare_failed`='warning', `snapshot_missing`='info', drift reasons per §3.5 below. | Q3-followup |
| **Q4** | **v1 scope:** publish-time capture + explicit admin compare endpoint. NO automatic hydrate fanout, NO scheduler, NO public-side compare. | §F Q4 |
| **Q4-endpoint** | **`POST /api/v1/admin/publications/{id}/compare`** — action endpoint, runs fresh compute, returns ComparatorResult. NO GET endpoint in v1 (no result caching layer). | Q4-followup |
| **Q5** | **Behavior:** admin badge + explicit operator refresh flow. NO publish gate in v1. | §F Q5 |
| **Q6** | **Missing observation:** dedicated `missing_state_changed` reason, separate from `value_changed`. | §F Q6 |
| **Q7** | **Public stale:** backend-computed/admin-only by default in v1. Public flag is optional/future, NOT in 3.1d scope. | §F Q7 |
| **Q8** | **Backend service reuse:** direct `ResolveService` reuse via DI. NO HTTP self-call. | §F Q8 |
| **Clone** | **Clone has no snapshots until first publish.** Matches DEBT-026 `document_state=None` reset pattern. Operator sees `snapshot_missing` reason on cloned publication until they republish. | Q1+Q2-followup |

## 2) Storage contract (Q1, Q2, Clone)

### 2.1 Table schema for `publication_block_snapshot`

Required columns and constraints are locked exactly as ratified, plus two justified columns for ResolveService input fidelity (`dims_json`, `members_json`) per §4 decision (c).

- PK: `id`
- FK: `publication_id -> publications.id` with `ON DELETE CASCADE`
- Unique: `UNIQUE(publication_id, block_id)`
- Index: `ix_publication_block_snapshot_publication_id`
- Column order in migration: `id, publication_id, block_id, cube_id, semantic_key, coord, period, dims_json, members_json, mapping_version_at_publish, source_hash_at_publish, value_at_publish, missing_at_publish, is_stale_at_publish, captured_at, created_at, updated_at`

Alembic naming convention: mirror existing phase pattern with next timestamped file under `backend/alembic/versions/` using slug format like `YYYYMMDD_HHMM_phase_3_1d_publication_block_snapshot.py`; upgrade creates table+constraints+index, downgrade drops index then table.

### 2.2 Clone semantics

Source read confirmed `clone_publication` exists and delegates clone row construction to repository `create_clone`. `create_clone` explicitly sets `document_state=None`, sets `status=DRAFT`, and does not set `published_at`, so `published_at` remains null on clone. Clone path does not write snapshot-like related tables today (only publication row + audit emission from endpoint layer).

Contract:
- cloned publication gets **no** `publication_block_snapshot` rows;
- first publish on clone performs first snapshot capture;
- comparator returns `stale_status="unknown"`, reason `snapshot_missing`, severity `info` until republish capture occurs.

### 2.3 Backwards compatibility for pre-3.1d publications

Publications published before snapshot rollout have no snapshot rows. Comparator contract is `unknown + [snapshot_missing] + info`.

Operator path:
- badge copy: “Snapshot pre-dates 3.1d. Re-publish to capture.”
- compare endpoint is diagnostic/read-only and does not recapture.
- explicit refresh flow in Q5 maps to republish action (`POST /{publication_id}/publish`) in v1.

Ambiguity surfaced for founder sign-off: whether future UX introduces a dedicated “refresh snapshot without status transition” action; recon locks v1 to republish-only refresh.

## 3) API surface (Q4-endpoint, Q8)

### 3.1 Endpoint contract

- Path: `POST /api/v1/admin/publications/{id}/compare`
- Auth: existing API-key middleware
- Request body: none
- 200: `PublicationComparatorResponse`
- 404: `PUBLICATION_NOT_FOUND`
- 401: middleware
- No-compare-possible cases still return 200 with `overall_status=unknown` and typed reasons (`snapshot_missing`, `compare_failed`).

### 3.2 Service contract (direct `ResolveService` reuse)

`PublicationStalenessService` injected with direct `ResolveService` instance via DI. No internal HTTP calls.

`BoundBlockReference` contract for publish-time capture:
- `block_id: str`
- `cube_id: str`
- `semantic_key: str`
- `dims: list[int]`
- `members: list[int]`
- `period: str | None`

Invocation: called from existing publish handler after successful publish mutation, before response return.

Failure policy: best-effort capture; publish success is not rolled back on snapshot capture errors.

Bound block extraction verdict (HALT-cleared): existing publish handler currently accepts no body. Therefore recon locks optional body extension on publish endpoint: `bound_blocks: list[BoundBlockReference] | None = Body(default=None)`.

### 3.3 Repository contract

`PublicationBlockSnapshotRepository` minimum methods:
- `upsert_for_block(...)`
- `get_for_publication(publication_id)`
- `delete_for_publication(publication_id)`

Upsert semantics locked: overwrite by `(publication_id, block_id)`, preserve `created_at`, bump `updated_at`, refresh all snapshot fields, set `captured_at` to publish action timestamp.

### 3.4 Response schema

Stale reasons:
- `mapping_version_changed`
- `source_hash_changed`
- `value_changed`
- `missing_state_changed`
- `cache_row_stale`
- `compare_failed`
- `snapshot_missing`

Statuses: `fresh`, `stale`, `unknown`

Severities: `info`, `warning`, `blocking`

Aggregation:
- overall status: stale > unknown > fresh
- overall severity: blocking > warning > info
- zero bound blocks: fresh/info.

### 3.5 Severity mapping

| Reason | Severity |
|---|---|
| mapping_version_changed | info |
| source_hash_changed | info |
| value_changed | warning |
| missing_state_changed | warning |
| cache_row_stale | warning |
| compare_failed | warning |
| snapshot_missing | info |

## 4) Comparator algorithm (Q3, Q6, Q8)

Locked compare behavior:
1. Iterate snapshot rows for publication.
2. Re-resolve current value through direct `ResolveService` using snapshot identity.
3. On resolve exceptions (`MappingNotFound...`, cache miss, invalid filters, unexpected), emit `compare_failed`.
4. On success, evaluate drift reasons: mapping version, source hash, value, missing state, current is_stale.
5. Compute stale status + severity from reason set.
6. For expected bound blocks absent in snapshot table, emit `snapshot_missing` with `unknown/info`.

Value comparison for `value_changed` is byte-equal string compare (canonical-string contract).

Coord-vs-dims/members verdict: **Option (c) chosen** — store raw dims/members alongside coord to keep resolve call mechanical and avoid decode coupling.

## 5) Capture flow (Q4 publish-time)

### 5.1 Invocation point

Publish endpoint (`publish_publication`) sets published status/timestamp via repository, then staleness capture executes best-effort prior to returning response.

### 5.2 Bound block extraction

Decision: explicit list at publish time via optional request body extension.

If `bound_blocks` omitted, publish remains successful and no snapshots are written; later compare surfaces `snapshot_missing`.

Frontend integration: required companion change for functional rollout; without it, 3.1d behaves diagnostically as unknown/missing.

### 5.3 Capture algorithm

For each bound block, call `ResolveService.resolve_value(...)`, then upsert snapshot row with resolve fingerprint and `captured_at`. Resolve failures are logged and skipped per-block.

## 6) Test plan

### 6.1 Unit tests
All listed unit cases from the ratified plan are required, including reason detection, severity aggregation, compare_failed handling, and byte-equal value normalization.

### 6.2 Repository tests
Required: upsert overwrite semantics, list retrieval behavior, FK cascade, unique constraint enforcement.

### 6.3 Integration tests
Required endpoint tests: 404, fresh/stale paths, pre-3.1d missing snapshots, clone missing snapshots, capture-failure non-blocking publish, severity aggregation, auth enforcement.

### 6.4 Pipeline test
Required end-to-end: publish with `bound_blocks` then compare over HTTP with real DB-backed resolve path (no mocks).

## 7) Drift detection touch list

Required in impl PR:
- `docs/api.md`
- `docs/architecture/BACKEND_API_INVENTORY.md`
- `docs/architecture/ROADMAP_DEPENDENCIES.md`
- `docs/architecture/ARCHITECTURE_INVARIANTS.md`

Optional/follow-up after frontend integration:
- `docs/architecture/FRONTEND_AUTOSAVE_ARCHITECTURE.md`
- `docs/architecture/FLUTTER_ADMIN_MAP.md`
- `docs/architecture/_DRIFT_DETECTION_TEMPLATE.md`
- `docs/architecture/AGENT_WORKFLOW.md`
- `docs/architecture/TEST_INFRASTRUCTURE.md`
- `docs/architecture/DEPLOYMENT_OPERATIONS.md`

## 8) DEBT entries to file

`docs/architecture/DEBT.md` was not found in this repo tree during pre-flight; recon still drafts entries for impl-time insertion into the canonical debt register path used in this repository.

- DEBT-NN1: 3.1d-deferred automatic hydrate fanout (low)
- DEBT-NN2: 3.1d-deferred scheduled background compare (low)
- DEBT-NN3: 3.1d-deferred public stale display (low)
- DEBT-NN4: 3.1d-followup coord-vs-dim/member storage (low, required because option (c) locked)

## 9) Risk inventory

1. Capture-time partial failure (medium, Q4) — mitigated via per-block missing diagnostics.
2. Publish/compare race (low, Q4-endpoint) — accepted transient inconsistency window.
3. Mapping deletion post-publish (medium, §4) — surfaced as `compare_failed`.
4. Coord encoding drift (low with option c) — mitigated by persisted dims/members.
5. Pre-3.1d operator confusion (medium, Q5) — explicit badge copy.
6. Frontend extension friction (high, §5.2) — frontend publish body extension required milestone.
7. Clone block-id stability uncertainty (medium-high, Q1+Q2) — clone resets `document_state=None`; no snapshot carryover avoids cross-publication key reuse coupling.

## 10) Migration order + implementation phasing

1. Alembic migration.
2. ORM model.
3. Snapshot repository.
4. Staleness service.
5. Staleness schemas.
6. Admin publications compare route.
7. Publish handler optional body + capture hook.
8. Tests (unit → repo → integration → pipeline).
9. Drift docs.
10. DEBT updates.

## 11) Pre-flight greps verification

Pre-flight checks completed; verbatim outputs are captured in Appendix B.

### Appendix B — Verbatim command outputs

```bash
grep -n "async def clone_publication\|def clone_publication" backend/src/services/publications/clone.py
26:async def clone_publication(*, session: AsyncSession, source_id: int) -> Publication:
```

```bash
grep -n "def publish_publication\|/{id}/publish\|async def publish" backend/src/api/routers/admin_publications.py
510:async def publish_publication(
```

```bash
grep -n "publish.*body\|PublicationPublishRequest\|publish.*Body(" backend/src/api/routers/admin_publications.py backend/src/schemas/publication.py
```

```bash
grep -nE "^### DEBT-[0-9]+" docs/architecture/DEBT.md | tail -5
grep: docs/architecture/DEBT.md: No such file or directory
```

```bash
grep -nE "ForeignKey.*publications.id|on_delete.*CASCADE" backend/src/models/* | head -10
backend/src/models/publication.py:91:        ForeignKey("publications.id", ondelete="SET NULL"),
```

```bash
grep -n "Body(default=None)\|Body(\.\.\..*default" backend/src/api/routers/* | head -10
```

```bash
nl -ba backend/src/services/publications/clone.py | sed -n '1,220p'
     1	"""Clone use-case for Publication."""
     2	from __future__ import annotations
     3	
     4	import json
     5	
     6	from sqlalchemy.exc import IntegrityError
     7	from sqlalchemy.ext.asyncio import AsyncSession
     8	
     9	from src.models.publication import Publication, PublicationStatus
    10	from src.repositories.publication_repository import PublicationRepository
    11	from src.services.publications.exceptions import (
    12	    PublicationCloneNotAllowedError,
    13	    PublicationNotFoundError,
    14	)
    15	from src.services.publications.lineage import (
    16	    compute_config_hash,
    17	    derive_clone_lineage_key,
    18	    derive_size_from_visual_config,
    19	)
    20	
    21	_COPY_PREFIX = "Copy of "
    22	_HASH_SLICE = 16
    23	_MAX_CLONE_VERSION_RETRIES = 3
    24	
    25	
    26	async def clone_publication(*, session: AsyncSession, source_id: int) -> Publication:
    27	    """Clone a published publication into a new draft."""
    28	    repo = PublicationRepository(session)
    29	
    30	    source = await repo.get_by_id(source_id)
    31	    if source is None:
    32	        raise PublicationNotFoundError()
    33	
    34	    if source.status != PublicationStatus.PUBLISHED:
    35	        status_val = source.status.value if hasattr(source.status, "value") else str(source.status)
    36	        raise PublicationCloneNotAllowedError(
    37	            publication_id=source_id,
    38	            current_status=status_val,
    39	        )
    40	
    41	    new_headline = source.headline if source.headline.startswith(_COPY_PREFIX) else f"{_COPY_PREFIX}{source.headline}"
    42	
    43	    size = derive_size_from_visual_config(source.visual_config)
    44	    new_config_hash = compute_config_hash(
    45	        chart_type=source.chart_type,
    46	        size=size,
    47	        title=new_headline,
    48	    )[:_HASH_SLICE]
    49	
    50	    fresh_review_json = json.dumps(
    51	        {"workflow": "draft", "history": [], "comments": []},
    52	    )
    53	
    54	    last_exc: IntegrityError | None = None
    55	    for attempt in range(_MAX_CLONE_VERSION_RETRIES):
    56	        if source.source_product_id is None:
    57	            new_version = 1
    58	        else:
    59	            latest = await repo.get_latest_version(source.source_product_id, new_config_hash)
    60	            new_version = (latest or 0) + 1
    61	        try:
    62	            clone = await repo.create_clone(
    63	                source=source,
    64	                new_headline=new_headline,
    65	                new_config_hash=new_config_hash,
    66	                new_version=new_version,
    67	                fresh_review_json=fresh_review_json,
    68	                lineage_key=derive_clone_lineage_key(source),
    69	            )
    70	            await session.commit()
    71	            return clone
    72	        except IntegrityError as exc:
    73	            await session.rollback()
    74	            last_exc = exc
    75	            if attempt == _MAX_CLONE_VERSION_RETRIES - 1:
    76	                raise
    77	            continue
    78	
    79	    assert last_exc is not None
    80	    raise last_exc
```

```bash
nl -ba backend/src/api/routers/admin_publications.py | sed -n '470,620p'
   470	    # value-change predicate so a PATCH that keeps ``workflow="published"``
   471	    # does not re-emit.
   472	    if new_workflow == "published" and new_workflow != previous_workflow:
   473	        await audit.log_event(
   474	            event_type=EventType.PUBLICATION_PUBLISHED,
   475	            entity_type="publication",
   476	            entity_id=str(publication.id),
   477	            metadata={
   478	                "from": previous_workflow,
   479	                "to": new_workflow,
   480	                "source": "patch_review",
   481	            },
   482	            actor="admin_api",
   483	        )
   484	
   485	    logger.info(
   486	        "publication_updated",
   487	        publication_id=publication.id,
   488	        fields=list(payload.keys()),
   489	        previous_workflow=previous_workflow,
   490	        new_workflow=new_workflow,
   491	    )
   492	    response.headers["ETag"] = compute_etag(publication)
   493	    return _serialize(publication)
   494	
   495	
   496	# ---------------------------------------------------------------------------
   497	# POST /api/v1/admin/publications/{publication_id}/publish
   498	# ---------------------------------------------------------------------------
   499	
   500	
   501	@router.post(
   502	    "/{publication_id}/publish",
   503	    response_model=PublicationResponse,
   504	    status_code=status.HTTP_200_OK,
   505	    summary="Publish a draft publication",
   506	    responses={
   507	        404: {"description": "Publication not found."},
   508	    },
   509	)
   510	async def publish_publication(
   511	    publication_id: int,
   512	    repo: PublicationRepository = Depends(_get_repo),
   513	    audit: AuditWriter = Depends(_get_audit),
   514	) -> PublicationResponse:
   515	    """Set status to PUBLISHED, stamp ``published_at``, and audit.
   516	
   517	    If the row already carries a ``review`` payload the endpoint also
   518	    mirrors ``review.workflow = "published"`` and appends a history
   519	    entry authored as ``"system"`` so the frontend can render the
   520	    transition in its timeline. Rows without a ``review`` payload are
   521	    published by status alone (no review sync is attempted).
   522	    """
   523	    publication = await repo.publish(publication_id)
   524	    if publication is None:
   525	        raise PublicationNotFoundError()
   526	
   527	    # Mirror into review.workflow when a review payload exists. We
   528	    # cannot know the ``fromWorkflow`` safely from the backend (no
   529	    # atomic snapshot), so leave it ``None`` — the frontend shape
   530	    # allows a null ``fromWorkflow`` for system-emitted entries.
   531	    publication = await _sync_workflow_from_status(
   532	        repo, publication, target_workflow="published",
   533	        summary="Published via admin endpoint",
   534	    )
   535	
   536	    await audit.log_event(
   537	        event_type=EventType.PUBLICATION_PUBLISHED,
   538	        entity_type="publication",
   539	        entity_id=str(publication.id),
   540	        metadata={"headline": publication.headline},
   541	        actor="admin_api",
   542	    )
   543	    logger.info("publication_published", publication_id=publication.id)
   544	    return _serialize(publication)
   545	
   546	
   547	# ---------------------------------------------------------------------------
   548	# POST /api/v1/admin/publications/{publication_id}/unpublish
   549	# ---------------------------------------------------------------------------
   550	
   551	
   552	@router.post(
   553	    "/{publication_id}/unpublish",
   554	    response_model=PublicationResponse,
   555	    status_code=status.HTTP_200_OK,
   556	    summary="Unpublish a publication (revert to DRAFT)",
   557	    responses={
   558	        404: {"description": "Publication not found."},
   559	    },
   560	)
   561	async def unpublish_publication(
   562	    publication_id: int,
   563	    repo: PublicationRepository = Depends(_get_repo),
   564	    audit: AuditWriter = Depends(_get_audit),
   565	) -> PublicationResponse:
   566	    """Revert the publication to DRAFT status and record an audit event.
   567	
   568	    The audit trail must be symmetric with :func:`publish_publication` —
   569	    there is currently no dedicated ``PUBLICATION_UNPUBLISHED`` member in
   570	    :class:`EventType`, so we reuse :attr:`EventType.PUBLICATION_PUBLISHED`
   571	    and distinguish the reversal via ``metadata.action = "unpublish"``
   572	    (with ``new_status`` for dashboard filtering).
   573	    """
   574	    publication = await repo.unpublish(publication_id)
   575	    if publication is None:
   576	        raise PublicationNotFoundError()
   577	
   578	    publication = await _sync_workflow_from_status(
   579	        repo, publication, target_workflow="draft",
   580	        summary="Unpublished via admin endpoint; returned to draft",
   581	    )
   582	
   583	    await audit.log_event(
   584	        event_type=EventType.PUBLICATION_PUBLISHED,
   585	        entity_type="publication",
   586	        entity_id=str(publication.id),
   587	        metadata={
   588	            "action": "unpublish",
   589	            "new_status": "DRAFT",
   590	            "headline": publication.headline,
   591	        },
   592	        actor="admin_api",
   593	    )
   594	    logger.info("publication_unpublished", publication_id=publication.id)
   595	    return _serialize(publication)
   596	
   597	
   598	@router.post(
   599	    "/{publication_id}/clone",
   600	    response_model=PublicationResponse,
   601	    status_code=status.HTTP_201_CREATED,
   602	    summary="Clone a published publication into a new draft",
   603	    responses={
   604	        404: {"description": "Publication not found."},
   605	        409: {"description": "Publication is not published and cannot be cloned."},
   606	    },
   607	)
   608	async def clone_publication_endpoint(
   609	    publication_id: int,
   610	    response: Response,
   611	    session: AsyncSession = Depends(get_db),
   612	) -> PublicationResponse:
   613	    """Clone a published publication into a new draft.
   614	
   615	    Sets ``ETag`` response header on the clone so the editor can use it as
   616	    the seed ``If-Match`` for the first PATCH (Phase 1.3 fork-path).
   617	    """
   618	    try:
   619	        clone = await clone_publication(session=session, source_id=publication_id)
   620	    except (PublicationNotFoundError, PublicationCloneNotAllowedError) as exc:
```
