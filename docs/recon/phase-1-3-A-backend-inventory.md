# Phase 1.3 Pre-Recon Part A — Backend Inventory

**Type:** READ-ONLY DISCOVERY (1 of 4 parts for 1.3 pre-recon)
**Scope:** backend code that the 412/ETag impl will touch.
**Date:** 2026-04-27

---

## §1.1 PATCH publication endpoint

Literal grep:

```
$ grep -rn 'router\.patch.*publication\|@.*\.patch.*publication' backend/src/api/
(no matches)

$ grep -rn '\.patch(' backend/src/api/
backend/src/api/routers/admin_publications.py:340:@router.patch(
```

> Note: the original spec used `backend/app/api/`; this repo uses `backend/src/api/`.

**File / line:** `backend/src/api/routers/admin_publications.py:340`

**Full handler signature** (from `backend/src/api/routers/admin_publications.py:340-355`):

```python
@router.patch(
    "/{publication_id}",
    response_model=PublicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Partial update of a publication",
    responses={
        404: {"description": "Publication not found."},
        422: {"description": "Validation failure."},
    },
)
async def update_publication(
    publication_id: int,
    body: PublicationUpdate,
    repo: PublicationRepository = Depends(_get_repo),
    audit: AuditWriter = Depends(_get_audit),
) -> PublicationResponse:
```

- **Path parameter:** `publication_id: int`
- **Body schema:** `PublicationUpdate` (Pydantic model, defined `backend/src/schemas/publication.py:152`)
- **`Depends(...)` count:** 2 (`_get_repo`, `_get_audit`)
- **Response model:** `PublicationResponse`
- **Default success status:** `200 OK`
- **Documented responses:** `404`, `422` (no `412` declared)
- **Body returns:** `_serialize(publication)` → `PublicationResponse` (`admin_publications.py:459`)

Gloss: PATCH endpoint exists at `/api/v1/admin/publications/{publication_id}`, returns 200 on success, raises `PublicationNotFoundError` (→404) when row missing. No conditional/precondition handling exists today.

---

## §1.2 Publication model — version-relevant columns

Literal find:

```
$ find backend/src/domain/publication -name '*.py'
(directory does not exist)

$ find backend/src -path '*publication*' -name '*.py'
backend/src/schemas/publication.py
backend/src/repositories/publication_repository.py
backend/src/models/publication.py
backend/src/services/publications/clone.py
backend/src/services/publications/__init__.py
backend/src/services/publications/exceptions.py
backend/src/services/publications/lineage.py
backend/src/api/routers/admin_publications.py
```

**ORM file:** `backend/src/models/publication.py`

Verbatim column list (from `backend/src/models/publication.py:80-155`):

```python
id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
headline: Mapped[str] = mapped_column(String(500), nullable=False)
chart_type: Mapped[str] = mapped_column(String(100), nullable=False)
s3_key_lowres: Mapped[str | None] = mapped_column(Text, nullable=True)
s3_key_highres: Mapped[str | None] = mapped_column(Text, nullable=True)
virality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
source_product_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
version: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
config_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
cloned_from_publication_id: Mapped[int | None] = mapped_column(
    ForeignKey("publications.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)
status: Mapped[PublicationStatus] = mapped_column(
    Enum(PublicationStatus, name="publication_status"),
    nullable=False,
    default=PublicationStatus.DRAFT,
    server_default="DRAFT",
    index=True,
)
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=lambda: datetime.now(timezone.utc),
    index=True,
)
eyebrow: Mapped[str | None] = mapped_column(String(255), nullable=True)
description: Mapped[str | None] = mapped_column(Text, nullable=True)
source_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
footnote: Mapped[str | None] = mapped_column(Text, nullable=True)
visual_config: Mapped[str | None] = mapped_column(Text, nullable=True)
review: Mapped[str | None] = mapped_column(Text, nullable=True)
document_state: Mapped[str | None] = mapped_column(Text, nullable=True)
updated_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
    onupdate=func.now(),
)
published_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
)
```

**Flagged version-relevant columns:**

| Column                | Present | Notes                                                                                       |
| --------------------- | ------- | ------------------------------------------------------------------------------------------- |
| `id`                  | ✅      | `int`, PK, autoincrement                                                                    |
| `updated_at`          | ✅      | `DateTime(timezone=True)`, **nullable**, `onupdate=func.now()` set                          |
| `version`             | ✅      | `int`, nullable=False, `default=1`, `server_default="1"` — used for product-lineage version |
| `config_hash`         | ✅      | `String(64)`, nullable                                                                      |
| `source_product_id`   | ✅      | `String(100)`, nullable, indexed                                                            |
| `content_hash`        | ✅      | `String(64)`, nullable                                                                      |
| `cloned_from_publication_id` | ✅ | FK → `publications.id`                                                                      |

`__table_args__` carries a unique constraint `uq_publication_lineage_version` on `(source_product_id, config_hash, version)` (`models/publication.py:71-78`).

Gloss: `updated_at` already exists with DB-level `onupdate=func.now()`; no dedicated optimistic-concurrency `row_version`/`etag` column exists today. `version` is product-lineage version, NOT row-revision counter.

---

## §1.3 PublicationRepository

Literal find:

```
$ find backend/src -name 'publication_repository.py'
backend/src/repositories/publication_repository.py
```

**File:** `backend/src/repositories/publication_repository.py`

Public method signatures (no bodies):

```python
def __init__(self, session: AsyncSession) -> None
async def get_latest_version(self, source_product_id: str, config_hash: str) -> int | None
async def create_published(
    self, *, headline: str, chart_type: str, s3_key_lowres: str, s3_key_highres: str,
    source_product_id: str | None, version: int, config_hash: str, content_hash: str,
    virality_score: float | None = None,
    status: PublicationStatus = PublicationStatus.PUBLISHED,
) -> Publication
async def create(
    self, *, headline: str, chart_type: str,
    s3_key_lowres: str | None = None, s3_key_highres: str | None = None,
    virality_score: float | None = None,
    status: PublicationStatus = PublicationStatus.DRAFT,
) -> Publication
async def create_clone(
    self, *, source: Publication, new_headline: str, new_config_hash: str,
    new_version: int, fresh_review_json: str,
) -> Publication
async def get_published(self, limit: int, offset: int) -> list[Publication]
async def get_published_sorted(self, limit: int, offset: int, sort: str = "newest") -> list[Publication]
async def get_by_id(self, publication_id: int) -> Publication | None
async def get_drafts(self, limit: int) -> list[Publication]
async def update_status(self, publication_id: int, status: PublicationStatus) -> None
async def update_s3_keys(self, publication_id: int, s3_key_lowres: str, s3_key_highres: str) -> None
async def update_s3_keys_and_publish(
    self, publication_id: int, s3_key_lowres: str, s3_key_highres: str,
    status: PublicationStatus,
) -> None
async def create_full(self, data: dict[str, Any]) -> Publication
async def update_fields(self, pub_id: int, data: dict[str, Any]) -> Publication | None
async def publish(self, pub_id: int) -> Publication | None
async def unpublish(self, pub_id: int) -> Publication | None
async def list_by_status(
    self, status_filter: PublicationStatus | None, limit: int, offset: int,
) -> list[Publication]
```

(Two private statics: `_published_order_clause`, `_serialize_visual_config`, `_serialize_review`, `_deserialize_review`.)

**Key observations:**

- `get_published_sorted` **exists** (line 232) — memory fact-check ✅.
- `update_fields` (line 452) is the canonical PATCH update path. It does **NOT** explicitly assign `updated_at`; instead it calls `setattr(publication, key, value)` for each key in `data`, then `await self._session.flush()` and `await self._session.refresh(publication)`. The `updated_at` column refresh therefore relies on the SQLAlchemy `onupdate=func.now()` trigger declared on the model — i.e. updates to `updated_at` happen at the ORM/DB layer, not in repository code.
- `update_status`, `update_s3_keys`, `update_s3_keys_and_publish` use `update(...).values(...)` core-style statements that *do not* set `updated_at` themselves (and core-style `update()` does NOT trigger ORM `onupdate=` in SQLAlchemy 2.x). `publish` and `unpublish` use the ORM-style attribute path (and therefore *will* trigger `onupdate`).

Gloss: `get_published_sorted` is present; `update_fields` is the PATCH path; only the ORM-style mutation paths actually bump `updated_at` via the model-level `onupdate=func.now()`, while the core-style `update_status`/`update_s3_keys` paths do not.

---

## §1.4 Existing exception handler pattern (DEBT-030 reference)

Literal grep:

```
$ grep -rn '_publication_validation_exception_handler\|publication_validation_exception\|register_exception_handlers' backend/src/
backend/src/main.py:25:from src.core.error_handler import register_exception_handlers
backend/src/main.py:151:register_exception_handlers(app)
backend/src/core/error_handler.py:11:    from src.core.error_handler import register_exception_handlers
backend/src/core/error_handler.py:14:    register_exception_handlers(app)
backend/src/core/error_handler.py:87:async def _publication_validation_exception_handler(
backend/src/core/error_handler.py:112:def register_exception_handlers(app: FastAPI) -> None:
backend/src/core/error_handler.py:117:        register_exception_handlers(app)
backend/src/core/error_handler.py:123:    app.add_exception_handler(RequestValidationError, _publication_validation_exception_handler)
```

**`register_exception_handlers` location:** `backend/src/core/error_handler.py:112` (called once from `backend/src/main.py:151`).

**`_publication_validation_exception_handler` location:** `backend/src/core/error_handler.py:87`.

**Full signature + body** (`backend/src/core/error_handler.py:87-109`):

```python
async def _publication_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Wrap PATCH admin/publications validation errors with structured code."""
    if request.url.path.startswith("/api/v1/admin/publications/") and request.method == "PATCH":
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=jsonable_encoder(
                {
                    "detail": {
                        "error_code": "PUBLICATION_UPDATE_PAYLOAD_INVALID",
                        "message": "The submitted changes are invalid.",
                        "details": {"validation_errors": exc.errors()},
                    }
                }
            ),
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder({"detail": exc.errors()}),
    )
```

- **Uses `jsonable_encoder`:** ✅ yes (DEBT-030 PR1 hotfix in place — line 95 and line 108).
- Imported at the top of the module: `from fastapi.encoders import jsonable_encoder` (line 23).
- Routes the body under `{"detail": {"error_code": ..., "message": ..., "details": {...}}}` — a key shape the 412 handler must mirror.
- `register_exception_handlers` body (lines 112-123):

```python
def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        SummaVisionError,
        _summa_vision_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(RequestValidationError, _publication_validation_exception_handler)
```

The other registered handler is `_summa_vision_exception_handler` (lines 53-84) which serves the older `{"error_code", "message", "detail"}` envelope for `SummaVisionError` subclasses.

Gloss: handler template lives at `error_handler.py:87` and is wired through `register_exception_handlers` at line 112. `jsonable_encoder` is already in use. The 412 handler must mirror the same `{"detail": {error_code, message, details}}` shape and route through `register_exception_handlers`.

---

## §1.5 Existing BackendApiError envelope structure

Literal grep:

```
$ grep -rn 'class.*BackendApi\|class.*PublicationInternalSerialization\|error_code.*=' backend/src/exceptions/ backend/src/core/
(backend/src/exceptions/ does not exist)

$ grep -rn 'class.*BackendApi\|class.*PublicationInternalSerialization\|error_code.*=' backend/src/
… backend/src/services/publications/exceptions.py:20:    error_code: str = "PUBLICATION_UNKNOWN_ERROR"
… backend/src/services/publications/exceptions.py:48:    error_code = "PUBLICATION_UPDATE_PAYLOAD_INVALID"
… backend/src/services/publications/exceptions.py:52:class PublicationInternalSerializationError(PublicationApiError):
… backend/src/services/publications/exceptions.py:56:    error_code = "PUBLICATION_INTERNAL_SERIALIZATION_ERROR"
…
```

> Note: there is **no** class named `BackendApiError` in the repo. The role implied by that name is filled by **two separate** hierarchies:

### Hierarchy A — `PublicationApiError` (HTTP-side, FastAPI `HTTPException` subclass)

**File:** `backend/src/services/publications/exceptions.py`

```python
class PublicationApiError(HTTPException):
    status_code_value: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "PUBLICATION_UNKNOWN_ERROR"
    message: str = "Publication action failed."

    def __init__(self, *, details: dict[str, Any] | None = None) -> None:
        detail_payload: dict[str, Any] = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if details is not None:
            detail_payload["details"] = details
        super().__init__(status_code=self.status_code_value, detail=detail_payload)


class PublicationNotFoundError(PublicationApiError):
    status_code_value = status.HTTP_404_NOT_FOUND
    error_code = "PUBLICATION_NOT_FOUND"
    message = "Publication not found."


class PublicationUpdatePayloadInvalidError(PublicationApiError):
    status_code_value = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "PUBLICATION_UPDATE_PAYLOAD_INVALID"
    message = "The submitted changes are invalid."


class PublicationInternalSerializationError(PublicationApiError):
    status_code_value = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "PUBLICATION_INTERNAL_SERIALIZATION_ERROR"
    message = "Could not save this publication due to a server data format issue."


class PublicationCloneNotAllowedError(PublicationApiError):
    status_code_value = status.HTTP_409_CONFLICT
    error_code = "PUBLICATION_CLONE_NOT_ALLOWED"
    message = "Only published publications can be cloned."

    def __init__(self, *, publication_id: int, current_status: str) -> None:
        super().__init__(details={
            "publication_id": publication_id,
            "current_status": current_status,
        })
```

- **`error_code` field:** ✅ class-level attribute on `PublicationApiError` and overridden per subclass.
- **Wire envelope** for any `PublicationApiError`-style raise:
  ```json
  {
      "detail": {
          "error_code": "PUBLICATION_NOT_FOUND",
          "message": "Publication not found.",
          "details": { "publication_id": 999999, "current_status": "DRAFT" }
      }
  }
  ```
  (FastAPI wraps the `detail` payload from `HTTPException` automatically; `details` only appears when the caller passed `details=`.)

### Hierarchy B — `SummaVisionError` (domain-side, custom global handler)

**File:** `backend/src/core/exceptions.py:21`

```python
class SummaVisionError(Exception):
    def __init__(
        self,
        message: str = "An unexpected error occurred",
        error_code: str = "SUMMA_VISION_ERROR",
        context: dict[str, object] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.context: dict[str, object] = context or {}
        super().__init__(self.message)
```

Subclasses (verbatim, all in `backend/src/core/exceptions.py`):
`WorkbenchError`, `DataSourceError`, `AIServiceError`, `StorageError`, `ValidationError`, `AuthError`, `NotFoundError`, `ConflictError`, `ESPPermanentError`, `ESPTransientError`.

- **`error_code` field:** ✅ instance attribute set in `__init__`.
- **Wire envelope** (served by `_summa_vision_exception_handler`, `error_handler.py:53-84`):
  ```json
  {
      "error_code": "DATASOURCE_ERROR",
      "message": "StatCan WDS returned HTTP 503",
      "detail": { "url": "...", "status_code": 503 }
  }
  ```
  Note the *flat* shape (no nested `"detail"` wrapper) — this differs from Hierarchy A, which nests under `"detail"`.

### Verbatim envelope assertion from existing tests

`backend/tests/api/test_admin_publications.py:683-698`:

```python
async def test_patch_publication_not_found_returns_structured_error_code(session_factory) -> None:
    """PATCH on non-existent publication returns structured PUBLICATION_NOT_FOUND."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/admin/publications/999999",
            json={"headline": "test"},
            headers=_auth_headers(),
        )

    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["error_code"] == "PUBLICATION_NOT_FOUND"
    assert body["detail"]["message"] == "Publication not found."
```

`backend/tests/api/test_admin_publications.py:736-758` (422 case):

```python
assert response.status_code == 422
body = response.json()
assert body["detail"]["error_code"] == "PUBLICATION_UPDATE_PAYLOAD_INVALID"
assert "validation_errors" in body["detail"]["details"]
```

Gloss: there is no `BackendApiError` class — the analogous role is split between `PublicationApiError` (HTTPException-based, nests under `detail`) and `SummaVisionError` (custom handler, flat top-level shape). The PATCH-side existing tests assert against the nested `detail.error_code`/`detail.message`/`detail.details.validation_errors` shape from Hierarchy A.

---

## §1.6 Integration test fixture pattern for PATCH publications

Literal grep:

```
$ find backend/tests/integration -name '*publication*.py'
(no matches — backend/tests/integration/ holds only cube/job/storage tests)

$ grep -rn 'def _make_app\|def make_app\|app.dependency_overrides' backend/tests/
backend/tests/test_publication_review_persistence.py:139:    app.dependency_overrides[_get_repo] = _override_repo
backend/tests/test_publication_review_persistence.py:140:    app.dependency_overrides[_get_audit] = _override_audit
backend/tests/test_publication_review_persistence.py:164:    app.dependency_overrides[_get_public_repo] = _override_public_repo
backend/tests/test_publication_review_persistence.py:165:    app.dependency_overrides[_get_public_storage] = _override_storage
backend/tests/test_publication_review_persistence.py:166:    app.dependency_overrides[get_gallery_limiter] = _override_limiter
backend/tests/api/test_clone_publication_endpoint.py:37:def _make_app(session_factory) -> FastAPI:
backend/tests/api/test_clone_publication_endpoint.py:69:    app.dependency_overrides[get_db] = _override_db
backend/tests/api/test_clone_publication_endpoint.py:70:    app.dependency_overrides[_get_repo] = _override_repo
backend/tests/api/test_clone_publication_endpoint.py:71:    app.dependency_overrides[_get_audit] = _override_audit
backend/tests/api/test_admin_publications.py:81:def _make_app(session_factory) -> FastAPI:
backend/tests/api/test_admin_publications.py:109:    app.dependency_overrides[_get_repo] = _override_repo
backend/tests/api/test_admin_publications.py:110:    app.dependency_overrides[_get_audit] = _override_audit
backend/tests/api/test_admin_publications.py:589:    app.dependency_overrides[_get_repo] = _override_repo
backend/tests/api/test_admin_publications.py:590:    app.dependency_overrides[_get_audit] = _override_audit
backend/tests/api/test_admin_publications.py:593:    app.dependency_overrides[_get_public_repo] = _override_repo
backend/tests/api/test_admin_publications.py:594:    app.dependency_overrides[_get_public_storage] = lambda: _ContractTestStorage()
backend/tests/api/test_admin_publications.py:596:    app.dependency_overrides[get_gallery_limiter] = lambda: InMemoryRateLimiter(
… (other public_graphics / download / etc fixtures elided)
```

> Note: there is **no** `backend/tests/integration/` file targeting publication PATCH. The canonical PATCH coverage lives at unit/router level under `backend/tests/api/test_admin_publications.py` (router-level integration with in-memory SQLite + DI overrides).

### Fixture A — canonical PATCH fixture: `_make_app` (admin-only)

`backend/tests/api/test_admin_publications.py:81-113`:

```python
def _make_app(session_factory) -> FastAPI:
    """Build a FastAPI app with the publications router + auth middleware."""
    app = FastAPI()
    register_exception_handlers(app)               # ← DEBT-030 PR1 lesson: present
    app.include_router(router)

    async def _override_repo() -> AsyncGenerator[PublicationRepository, None]:
        async with session_factory() as session:
            try:
                yield PublicationRepository(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_audit() -> AsyncGenerator[AuditWriter, None]:
        async with session_factory() as session:
            try:
                yield AuditWriter(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[_get_repo] = _override_repo
    app.dependency_overrides[_get_audit] = _override_audit

    app.add_middleware(AuthMiddleware, admin_api_key="test-admin-key")
    return app
```

- **Overrides count:** 2 (`_get_repo`, `_get_audit`).
- **Calls `register_exception_handlers(app)`:** ✅ yes (line 88).
- **Auth middleware:** added (`AuthMiddleware`).
- **DB:** in-memory SQLite via per-test `engine` fixture (lines 61-78), `Base.metadata.create_all` for schema.

### Fixture B — admin + public combined: `_make_admin_and_public_app`

`backend/tests/api/test_admin_publications.py:565-601`:

- **Overrides count:** 5 (`_get_repo`, `_get_audit`, `_get_public_repo`, `_get_public_storage`, `get_gallery_limiter`).
- **Calls `register_exception_handlers(app)`:** ❌ **NO** — does *not* call `register_exception_handlers`. Any new 412 test that reuses this fixture and expects the structured envelope would fail (this is exactly the DEBT-030 PR1 trap).

### Fixture C — clone endpoint fixture: `test_clone_publication_endpoint._make_app`

`backend/tests/api/test_clone_publication_endpoint.py:37-?`:

- **Overrides count:** 3 (`get_db`, `_get_repo`, `_get_audit`).
- **Calls `register_exception_handlers`:** (not shown by the grep above — would need a follow-up read; flagged for Part D).

### Fixture D — review persistence: `test_publication_review_persistence.py`

- **Overrides count:** 5 (`_get_repo`, `_get_audit`, `_get_public_repo`, `_get_public_storage`, `get_gallery_limiter`).
- **Calls `register_exception_handlers`:** (not shown by the grep above; flagged for Part D).

Gloss: the canonical PATCH test fixture is `backend/tests/api/test_admin_publications.py::_make_app`. It overrides `_get_repo` + `_get_audit` (2 deps) and **does** call `register_exception_handlers(app)`. The combined admin+public fixture in the same file does **not** register exception handlers — any new PATCH-412 test that needs the structured envelope must use `_make_app` (or the founder must add `register_exception_handlers(app)` to whichever fixture is reused).

---

## Summary Report

```
GIT REMOTE: http://local_proxy@127.0.0.1:38769/git/Inneren12/Summa-vision-can
DOC PATH: docs/recon/phase-1-3-A-backend-inventory.md

§1.1 PATCH endpoint:           backend/src/api/routers/admin_publications.py:340
  deps count: 2 (_get_repo, _get_audit)
  body schema: PublicationUpdate

§1.2 Publication model:        backend/src/models/publication.py
  has updated_at: yes (nullable=True, onupdate=func.now())
  has version column: yes (product-lineage version, NOT row-revision)
  has config_hash: yes (String(64), nullable)

§1.3 PublicationRepository:    backend/src/repositories/publication_repository.py
  get_published_sorted exists: yes (line 232)
  update method touches updated_at: indirectly — update_fields uses ORM setattr+flush so model-level onupdate fires; update_status/update_s3_keys use core update() and do NOT trigger onupdate

§1.4 Existing 422 handler:     backend/src/core/error_handler.py:87
  uses jsonable_encoder: yes (line 95 + line 108)
  register_exception_handlers location: backend/src/core/error_handler.py:112 (wired in backend/src/main.py:151)

§1.5 BackendApiError class:    NONE FOUND — split between PublicationApiError (backend/src/services/publications/exceptions.py:16) and SummaVisionError (backend/src/core/exceptions.py:21)
  error_code field present: yes (both hierarchies)

§1.6 Integration test fixture: backend/tests/api/test_admin_publications.py:81 (_make_app)
  dependency_overrides count: 2 (_get_repo, _get_audit)
  registers exception handlers: yes (line 88)

VERDICT: COMPLETE
```

---

**End of Part A.**
