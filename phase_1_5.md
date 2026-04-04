# Phase 1.5: Persistence Layer (Pack E)
Здесь мы внедряем базу данных. Без нее ни галерея на сайте, ни очередь для админки работать не будут.

## PR-39: Database Schema & SQLAlchemy Models

```
Role: Database Architect.
Task: Execute PR-39 for the "Summa Vision" project.
Context (Human): Implement the database layer. We need to persist generated graphics, email leads, and LLM requests (for cost tracking). MVP uses SQLite, Production uses PostgreSQL.
```

<ac-block id="Ph1.5-PR39-AC1">
**Acceptance Criteria for PR39 (SQLAlchemy Models):**
- [ ] Install `SQLAlchemy` 2.0 (async), `alembic`, `aiosqlite`, and `asyncpg`.
- [ ] Create base declarative models:
      - `Publication`: id, headline, chart_type, s3_key_lowres, s3_key_highres, virality_score, created_at, status (Enum: DRAFT, PUBLISHED).
      - `Lead`: id, email, ip_address, asset_id, is_b2b, company_domain, created_at, **[FIX]** `esp_synced: bool = False`, **[FIX]** `esp_sync_failed_permanent: bool = False`.
      - `LLMRequest`: id, prompt_hash, response_json, tokens_used, cost_usd, created_at.
- [ ] Set up `AsyncSession` via Dependency Injection (`get_db` FastAPI dependency).
- [ ] CRITICAL ARCHITECTURE: Use `DATABASE_URL` from `BaseSettings`. Do not hardcode connection strings. Configure Alembic and generate the initial migration.
- [ ] **[FIX]** The `Lead.esp_synced` field is required by Phase 5 (PR-34/49) for the ESP failsafe mechanism. The `esp_sync_failed_permanent` field marks leads where the ESP returned a 4xx client error (e.g., invalid email on Beehiiv side) so they are never retried.
- [ ] Unit Tests: Use an in-memory SQLite fixture. Create a `Publication` record, read it back, and assert all fields match. Create a `Lead` with `esp_synced=False`, assert default value persists.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/core/database.py`, `/backend/src/models/*.py`
- [ ] Test location: `/backend/tests/core/test_database.py`
</ac-block>

---

## PR-40: Repository Layer (CRUD Operations)

```
Role: Python Backend Engineer.
Task: Execute PR-40 for the "Summa Vision" project.
Context (Human): Isolate SQL queries from business logic. Services must never import SQLAlchemy models directly; they must use Repositories.
```

<ac-block id="Ph1.5-PR40-AC1">
**Acceptance Criteria for PR40 (Repository Pattern):**
- [ ] Create `PublicationRepository` with `create(...)`, `get_published(limit, offset)`, `update_status(id, status)`, **[FIX]** `get_drafts(limit: int) -> list[Publication]`.
- [ ] Create `LeadRepository` with `create(...)`, `exists(email, asset_id) -> bool` (for deduplication), **[FIX]** `get_unsynced(limit: int) -> list[Lead]` (where `esp_synced=False AND esp_sync_failed_permanent=False`), **[FIX]** `mark_synced(lead_id)`, **[FIX]** `mark_permanently_failed(lead_id)`.
- [ ] Create `LLMRequestRepository` with `log_request(prompt_hash, response, tokens, cost)`.
- [ ] CRITICAL ARCHITECTURE: All repositories MUST accept `AsyncSession` via DI in their constructor. No global DB sessions.
- [ ] **[FIX]** `get_drafts()` is required by Phase 2 `GET /api/v1/admin/queue` to fetch DRAFT publications for the Flutter admin panel.
- [ ] Unit Tests: Use in-memory SQLite. Test a full CRUD cycle for each repository. Specifically test the `exists()` deduplication logic for leads. **[FIX]** Test `get_unsynced()` returns only leads where both flags are False.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/repositories/*.py`
- [ ] Test location: `/backend/tests/repositories/*.py`
</ac-block>

---

## PR-41: Public Graphics Endpoint (Gallery API)

```
Role: Python Backend Engineer.
Task: Execute PR-41 for the "Summa Vision" project.
Context (Human): Provide a public, paginated API for the Next.js frontend gallery to fetch approved infographics.
```

<ac-block id="Ph1.5-PR41-AC1">
**Acceptance Criteria for PR41 (Public Gallery API):**
- [ ] Create router `GET /api/v1/public/graphics`.
- [ ] Return a paginated list of `PublicationResponse` schemas. Support query params: `?limit=12&offset=0&sort=newest`.
- [ ] CRITICAL ARCHITECTURE: This is a public endpoint. Implement a simple rate limit (30 req/min per IP) using the `InMemoryRateLimiter` (configurable, see PR-31 note below).
- [ ] Integrate `StorageInterface.generate_presigned_url(s3_key_lowres, ttl=3600)` to include secure preview URLs in the response.
- [ ] **[FIX]** Add `Cache-Control: public, max-age=3600` response header to align with the Next.js ISR `revalidate: 3600` setting from Phase 4 (PR-33).
- [ ] Unit Tests: Mock `PublicationRepository` and `StorageInterface`. Assert pagination limits, JSON schema, and Cache-Control header presence.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/api/routers/public_graphics.py`
</ac-block>
