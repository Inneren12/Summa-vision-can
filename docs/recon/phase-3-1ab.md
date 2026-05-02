# Phase 3.1ab Recon — SemanticMappingValidator + SemanticMappingService

## 0) Verification preflight
- Workspace clean check: `git status --short` returned no output (clean).
- Remote check: `git remote -v` returned no output (no remotes configured).
- No AGENTS.md found under repo-parent scan: `find .. -name AGENTS.md -print` returned no results.

## §A. `semantic_mappings.dimension_filters` JSONB shape
### A1 — Migration findings (`f3b8c2e91a4d`)
- The migration **does not create** a top-level `dimension_filters` column; it creates a `config` JSONB column (`postgresql.JSONB` with SQLite JSON variant).
- No DB-level JSON shape constraints are enforced (no CHECK on JSON schema; only `nullable=False`).
- Validation-relevant columns present: `cube_id`, `semantic_key`, `label`, `description`, `config`, `is_active`, `version`, `updated_by`, timestamps, and unique `(cube_id, semantic_key)`.

### A2 — ORM model (`backend/src/models/semantic_mapping.py`)
`SemanticMapping` fields and Python-side types:
- `id: int`
- `cube_id: str`
- `semantic_key: str`
- `label: str`
- `description: str | None`
- `config: dict`
- `is_active: bool`
- `version: int`
- `created_at: datetime`
- `updated_at: datetime`
- `updated_by: str | None`

Model docstring confirms `dimension_filters` lives inside `config` and shows example shape using name-keyed dict (`{"Geography": "Canada", ...}`).

### A3 — Pydantic schema (`backend/src/schemas/semantic_mapping.py`)
- `SemanticMappingConfig.dimension_filters: dict[str, str]`.
- `SemanticMappingCreate` carries top-level fields + `config: SemanticMappingConfig`.
- `SemanticMappingUpdate` is patch-style and allows optional `config: SemanticMappingConfig | None`.
- There is **no POST/PATCH-specific flattened `dimension_filters` field**; it is nested in `config`.

### A4 — Seed CLI + YAML reality
- Seed CLI reads YAML rows into `SemanticMappingCreate(**raw)` and passes them to `repo.upsert_by_key` directly.
- Current seed YAML (`backend/src/services/semantic/seed/cpi.yaml`) uses:
```yaml
config:
  dimension_filters:
    Geography: "Canada"
    Products: "All-items"
```
This is dict keyed by dimension `name_en` with member `name_en` values.

### A5 — Canonical shape decision (recon output)
**Current in-repo canonical shape is Option C** (dict keyed by dimension name, values are member names), because both schema type and live seed file enforce/instantiate that shape.

**Critical ambiguity vs founder-locked 3.1ab behavior:** locked validator behavior requires strict `member_id` checks, but current mapping schema carries only `dict[str, str]` labels, no IDs. This is a concrete contract mismatch and must be founder-decided before impl.

---

## §B. Validator design (pure function + service wrapper)
### B1 — Pure function
Recommended module: `backend/src/services/semantic_mappings/validation.py` (new service namespace, matching `services/statcan/*` layering and keeping semantic validation out of repository).

Given existing shape, two candidate signatures:
1) **If schema remains unchanged (current repo reality):**
```python
def validate_mapping_against_cache(*, cube_id: str, product_id: int,
                                   dimension_filters: dict[str, str],
                                   cache_entry: CubeMetadataCacheEntry) -> ValidationResult
```
2) **If founder aligns to locked member-id rule:** schema must evolve before validator can do strict ID validation.

Pure function constraints feasible: no I/O/logger/clock, return aggregate `ValidationResult` only.

### B2 — ValidationResult shape
Proposed dataclasses from prompt are UI-compatible for rendering a list of blocking errors plus optional hint fields.

Note: with current `dict[str, str]` mapping shape, `dimension_id` and `member_id` in errors may often be `None` unless implementation resolves names→IDs first.

### B3 — Fuzzy strategy feasibility
With current shape (`member name`, not member_id), fuzzy hint is feasible (name-to-name within matched dimension). With locked future strict-by-member_id behavior, fuzzy hint requires carrying an attempted member name alongside ID; otherwise there is no string to match.

**Recon recommendation:** founder decides one of:
- Keep name-based mapping for 3.1ab and validate by normalized EN name equality (contradicts locked strict-ID rule), or
- Migrate mapping contract to include IDs (and optionally preserve names for hinting/UI), enabling strict-ID + hint.

### B4 — Service wrapper
Proposed `SemanticMappingService.upsert_validated(...)` should:
1. call `metadata_cache.get_or_fetch(cube_id, product_id)`;
2. run pure validator;
3. raise metadata-validation-family exception on errors;
4. open DB session + call repository `upsert_by_key`.

DI pattern with `session_factory` and collaborators is consistent with `StatCanMetadataCacheService` constructor style (factory + injected collaborators).

### B5 — one method vs two
Use **single `upsert_validated`** to mirror existing repository `upsert_by_key` behavior and seed idempotence path. Separate create/update only needed once HTTP PATCH semantics are wired in 3.1b.

---

## §C. Exception hierarchy
### C1 — Proposed module
Create `backend/src/services/semantic_mappings/exceptions.py` with:
- `MetadataValidationError`
- `CubeNotInCacheError`
- `DimensionMismatchError`
- `MemberMismatchError`

### C2 — Re-wrap mapping recommendation
Recommend re-wrap for uniform admin/UI contract:
- `StatCanUnavailableError` -> `CubeNotInCacheError`
- `CubeNotFoundError` -> `CubeNotInCacheError`
- `CubeMetadataProductMismatchError` -> `MetadataValidationError` containing `CUBE_PRODUCT_MISMATCH`

### C3 — DEBT-030 envelope integration
Frontend currently centralizes allowed backend codes in `KNOWN_BACKEND_ERROR_CODES` and resolver mapping (`frontend-public/src/lib/api/errorCodes.ts`). 3.1ab impl scope should include adding new codes and i18n mappings (even if endpoints wire in 3.1b, code dictionaries must be prepared consistently).

---

## §D. Wire-in point (admin save flow)
### D1 result
`grep -rn "semantic_mappings\|SemanticMapping" backend/src/api/` returned no matches.

Conclusion: no admin semantic-mappings endpoints exist yet in backend API tree. This confirms 3.1ab remains service-layer-only, with HTTP wiring in 3.1b.

### D2/D3
- 3.1ab should add internal service + validator + tests only.
- No endpoint refactor scope currently required.

---

## §E. CPI seed YAML interaction
### E1
Current seed CLI bypasses validator (calls repository directly), matching 3.1a comments.

### E2 recommendation
Because `get_or_fetch` may need live StatCan on first cube seed, recommend:
- default: validated path (fail fast if StatCan unavailable and cache miss),
- optional `--skip-validation` escape hatch for offline/dev workflows.

Rationale: preserves production correctness by default while allowing controlled local bootstrapping.

### E3
Recommend migrating seed CLI in 3.1ab (mechanics only), while CPI content updates remain post-merge per locked scope.

---

## §F. Test plan inventory (proposed)
Target **17 tests**:
- Pure validator unit: 7
- Service unit: 7
- Integration (service+repo+cache): 2
- Seed CLI path: 1

Notes:
- If founder keeps current name-based shape, include name-normalization tests.
- If founder switches to ID-based shape, include conversion/compat tests and explicit schema failure tests for legacy YAML.

---

## §G. Architecture docs touch list
- `docs/modules/statcan.md`: add short cross-reference to semantic mapping validator consumption of cache service.
- `docs/architecture/BACKEND_API_INVENTORY.md`: no new endpoints; add internal-service note only if there is a suitable section.
- Semantic mappings module doc: no dedicated `docs/modules/semantic_mappings.md` found in this scan; propose creating it in impl.
- `docs/architecture/ARCHITECTURE_INVARIANTS.md`: no new invariants; reinforce ARCH-PURA-001 + ARCH-DPEN-001 usage in implementation notes.
- `_DRIFT_DETECTION_TEMPLATE.md`: evaluate during impl; likely no immediate drift entry unless public contract shifts (e.g., schema shape migration).

---

## §H. DEBT, glossary, ROADMAP
### H1 — max DEBT id (repo truth)
Command output:
```bash
grep -oE "DEBT-[0-9]+" DEBT.md | sort -u | tail -5
DEBT-047
DEBT-048
DEBT-049
DEBT-050
DEBT-051
```
Next available: **DEBT-052**.

### H2 — proposed DEBT entries
1) **DEBT-052**
- Source: Phase 3.1ab recon
- Added: 2026-05-01
- Severity: medium
- Category: architecture
- Status: active
- Description: Semantic mapping config currently stores `dimension_filters` as EN label pairs (`dict[str,str]`), while 3.1ab validator contract requires strict numeric `member_id` validation.
- Impact: Cannot implement locked strict-ID validation without schema/seed contract migration or dual-shape compatibility layer.
- Resolution: Decide canonical persisted shape and migration plan; implement adapter/deprecation policy.
- Target: Phase 3.1ab implementation decision gate.

2) **DEBT-053**
- Source: Phase 3.1ab recon
- Added: 2026-05-01
- Severity: low
- Category: ops
- Status: active
- Description: Fuzzy hint proposal is EN-name-centric; FR-only or non-canonical labels may not produce suggestions.
- Impact: Reduced operator hint quality in bilingual edge cases; no correctness risk (blocking decision unchanged).
- Resolution: Add locale-aware fuzzy strategy (EN+FR; transliteration/normalization).
- Target: Post-3.1c UX refinement.

### H3 — glossary / i18n proposals
Proposed keys (EN / RU):
- `errors.backend.metadata_validation_failed.title` — EN: "Metadata validation failed" / RU: "Проверка метаданных не пройдена"
- `errors.backend.metadata_validation_failed.body` — EN: "The mapping does not match StatCan cube metadata." / RU: "Сопоставление не соответствует метаданным куба StatCan."
- `errors.backend.dimension_not_found` — EN: "Dimension not found in cube metadata." / RU: "Измерение не найдено в метаданных куба."
- `errors.backend.member_not_found` — EN: "Member not found in dimension." / RU: "Элемент не найден в измерении."
- `errors.backend.cube_product_mismatch` — EN: "Cube ID and product ID do not match cached metadata." / RU: "Cube ID и product ID не соответствуют кэшированным метаданным."

Also add wire codes to frontend known-code map when backend begins emitting them.

### H4
ROADMAP not modified in recon.

---

## §I. Open questions for founder approval
1. **Canonical `dimension_filters` shape conflict.**
   - Context: DB/schema/seed are name-based (`dict[str,str]`), but locked 3.1ab behavior expects strict numeric member-id checks.
   - Options: keep name-based (deviates from lock) vs migrate to ID-based (requires schema+seed contract updates) vs dual-shape interim.
   - Recommendation: approve ID-based canonical target with explicit migration/compat plan; otherwise locked behavior is unimplementable as specified.

2. **Fuzzy hint input source.**
   - Context: If mapping carries only IDs, fuzzy name hint needs an input label to compare.
   - Options: add optional `member_name_en` in payload; retain raw user input in request DTO for hinting only; drop hint feature.
   - Recommendation: add optional label field in write schema for hint-only diagnostics.

3. **Service API shape: single upsert vs split create/update.**
   - Context: repository already models idempotent upsert.
   - Recommendation: one `upsert_validated` now; derive create/update orchestration at 3.1b endpoint layer.

4. **Cache exception bubbling vs re-wrap.**
   - Context: cache service already has rich exceptions, but admin/UI wants uniform metadata-validation family.
   - Recommendation: re-wrap in service for stable downstream contract.

5. **DEBT-030 contract integration timing.**
   - Context: frontend known code list is explicit; unknown codes degrade to fallback.
   - Recommendation: include backend+frontend code dictionary updates in 3.1ab impl even if endpoint exposure lands in 3.1b.

6. **Admin endpoint existence confirmation / dead-service period.**
   - Context: no semantic mapping endpoints found under `backend/src/api`.
   - Recommendation: accept intentional temporary dead-service state until 3.1b wires routes.

7. **Seed CLI behavior when StatCan unavailable on first seed.**
   - Context: `get_or_fetch` needs network on cache miss.
   - Recommendation: validation-on by default with clear failure; optional `--skip-validation` for controlled offline use.

8. **Additional DEBT beyond EN-only fuzzy.**
   - Context: major gap is shape mismatch (DEBT-052). EN-only fuzzy becomes secondary (DEBT-053).
   - Recommendation: track both; make DEBT-052 blocking for final impl design.

---

## Command log excerpts used for this recon
- `git status --short && git remote -v` -> no output (clean repo; no remotes configured).
- `find .. -name AGENTS.md -print` -> no output.
- `grep -rn "semantic_mappings\|SemanticMapping" backend/src/api/ || true` -> no output.
- `grep -oE "DEBT-[0-9]+" DEBT.md | sort -u | tail -5` -> DEBT-047..DEBT-051.
- Source reads: `sed -n` on migration/model/schema/repository/cache-service/seed files listed in this document.
