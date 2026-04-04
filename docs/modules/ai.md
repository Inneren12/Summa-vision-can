# Module: AI Services

**Package:** `backend.src.services.ai`
**Purpose:** Provider-agnostic LLM abstraction layer with cost tracking, budget alerting, and data-aware response caching.

## Package Structure

```
services/ai/
├── __init__.py
├── llm_interface.py     ← Abstract LLMInterface + GeminiClient
├── llm_cache.py         ← Data-aware TTL cache (24h default)
├── cost_tracker.py      ← Cost calculation + daily budget alerts
├── schemas.py           ← ContentBrief + ChartType (LLM output)
└── scoring_service.py   ← BriefGenerationService (batch scoring)

core/
└── prompt_loader.py   ← YAML prompt template loader

prompts/
└── journalist.yaml    ← System prompt for dataset virality scoring
```

## Classes & Functions

### `LLMInterface` (llm_interface.py) — ✅ Complete

Abstract base class defining the provider-agnostic LLM contract.

```python
class LLMInterface(ABC):
    async def generate_text(self, prompt: str, *, data_hash: str = "") -> str: ...
    async def generate_structured(self, prompt: str, schema: type[BaseModel], *, data_hash: str = "") -> BaseModel: ...
```

- `generate_text(prompt, data_hash)` — Generate free-form text. Uses cache when `data_hash` is provided.
- `generate_structured(prompt, schema, data_hash)` — Generate and validate structured JSON against a Pydantic model.

### `GeminiClient(LLMInterface)` (llm_interface.py) — ✅ Complete

Concrete implementation backed by Google Gemini via `google-genai` SDK.

```python
class GeminiClient(LLMInterface):
    def __init__(
        self,
        *,
        settings: Settings,          # API key, model name, budget
        session: AsyncSession,       # For cost persistence / budget queries
        repository: LLMRequestRepository,  # To log each API call
        cache: LLMCache,             # Response cache
        pricing: dict[str, dict[str, float]] | None = None,  # Override pricing
    ) -> None: ...
```

**Constructor Dependencies (ARCH-DPEN-001):**
- `Settings` — API key from `GEMINI_API_KEY`, model from `GEMINI_MODEL`, budget from `DAILY_LLM_BUDGET`.
- `AsyncSession` — For cost tracking SQL queries.
- `LLMRequestRepository` — For persisting API call logs.
- `LLMCache` — For checking/storing cached responses.

**Behaviour:**
1. Checks `LLMCache` **before** calling the API.
2. On cache miss: calls Gemini → logs via `LLMRequestRepository` → checks budget → caches response.
3. On API error: catches `google.genai.errors.APIError` and wraps it in `AIServiceError`.

### `LLMCache` (llm_cache.py) — ✅ Complete

In-memory TTL cache with data-aware invalidation.

```python
class LLMCache:
    def __init__(self, *, ttl_seconds: int = 86_400, max_size: int = 1024) -> None: ...

    @staticmethod
    def build_key(prompt: str, data_hash: str) -> str: ...  # PURE (ARCH-PURA-001)
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def clear(self) -> None: ...
    def size(self) -> int: ...  # property
```

**Cache Key Format:** `sha256(prompt) + "_" + sha256(data_hash)`

- `data_hash` should be derived from input DataFrame metadata or StatCan cube IDs.
- Ensures cache invalidation when new StatCan data is released, even if prompt is identical.
- `build_key` is a **pure function** — no I/O (ARCH-PURA-001).
- Backed by `cachetools.TTLCache`.

### `calculate_cost()` (cost_tracker.py) — ✅ Complete

Pure function to compute USD cost from token counts.

```python
def calculate_cost(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    pricing: dict[str, dict[str, float]],
) -> float: ...
```

**Pricing dict format:** per-million-token rates, e.g. `{"gemini-2.0-flash": {"input": 0.10, "output": 0.40}}`.

### `log_and_check_budget()` (cost_tracker.py) — ✅ Complete

Async function that sums today's `cost_usd` from `llm_requests` table and logs a `WARNING` if the total exceeds `DAILY_LLM_BUDGET`.

```python
async def log_and_check_budget(
    *,
    session: AsyncSession,
    budget_limit: float,
) -> float: ...  # Returns today's total spend
```

### `ChartType` (schemas.py) — ✅ Complete

String enum of supported chart types for infographic generation.

```python
class ChartType(str, Enum):
    LINE = "LINE"
    BAR = "BAR"
    SCATTER = "SCATTER"
    AREA = "AREA"
    STACKED_BAR = "STACKED_BAR"
    HEATMAP = "HEATMAP"
```

### `ContentBrief` (schemas.py) — ✅ Complete

Frozen Pydantic V2 model representing the structured LLM output for dataset virality assessment. Passed as the `schema` parameter to `GeminiClient.generate_structured()`.

```python
class ContentBrief(BaseModel):
    model_config = ConfigDict(frozen=True)

    virality_score: float = Field(ge=1.0, le=10.0)
    headline: str = Field(min_length=1, max_length=280)
    bg_prompt: str = Field(min_length=1)
    chart_type: ChartType
    reasoning: str | None = None
```

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `virality_score` | `float` | `ge=1.0, le=10.0` | Viral potential score |
| `headline` | `str` | `min_length=1, max_length=280` | Social media headline |
| `bg_prompt` | `str` | `min_length=1` | AI image generation prompt |
| `chart_type` | `ChartType` | enum | Recommended chart type |
| `reasoning` | `str \| None` | optional | LLM reasoning (debug only) |

### `BriefGenerationService` (scoring_service.py) — ✅ Complete

Core business-logic orchestrator that scores StatCan datasets for virality and persists qualifying results as DRAFT publications.

```python
class BriefGenerationService:
    def __init__(
        self,
        *,
        llm: LLMInterface,
        prompt_loader: PromptLoader,
        publication_repo: PublicationRepository,
        virality_threshold: float = 7.0,
    ) -> None: ...

    async def score_datasets(self, datasets: list[CubeMetadataResponse]) -> list[Publication]: ...
    async def score_single(self, dataset: CubeMetadataResponse) -> Publication | None: ...
```

**Constructor Dependencies (ARCH-DPEN-001):**
- `LLMInterface` — provider-agnostic LLM client.
- `PromptLoader` — for rendering the `journalist` prompt template.
- `PublicationRepository` — for persisting DRAFT publications.
- `virality_threshold` — configurable minimum score (default `7.0`).

**Behaviour (`score_datasets`):**
1. For each dataset, builds a `sha256(cube_id:release_date)` cache hash.
2. Renders the `journalist` prompt via `PromptLoader.render()`.
3. Calls `LLMInterface.generate_structured(prompt, ContentBrief, data_hash=hash)`.
4. If `virality_score >= virality_threshold` → persists via `PublicationRepository.create()` with `status=DRAFT`, `s3_key_lowres=None`, `s3_key_highres=None`.
5. If below threshold → logs `DEBUG` and skips.
6. If `AIServiceError` → logs `error` with cube ID and **continues** processing (fault-tolerant).
7. Logs a `structlog.info` summary at batch end: `total`, `persisted`, `skipped`, `errors`.

**`score_single`:** Convenience wrapper → calls `score_datasets([dataset])`, returns single `Publication` or `None`.

### `PromptLoader` (core/prompt_loader.py) — ✅ Complete

Loads and renders YAML-based system prompts. Receives `prompts_dir: Path` via constructor (ARCH-DPEN-001).

```python
class PromptLoader:
    def __init__(self, prompts_dir: Path) -> None: ...
    def load(self, name: str) -> str: ...
    def render(self, name: str, **kwargs: object) -> str: ...
```

- `__init__(prompts_dir)` — accepts the directory path containing `*.yaml` prompt files.
- `load(name)` — reads `{prompts_dir}/{name}.yaml`, returns the `system_prompt` string.
- `render(name, **kwargs)` — loads the prompt and calls `.format(**kwargs)` to inject dynamic values.
- All errors (missing file, malformed YAML, missing key) raise `ValidationError` from `src.core.exceptions`.
- Uses `PyYAML` (`yaml.safe_load`). Pure I/O — no database, no HTTP (ARCH-PURA-001).

## Configuration (Settings fields)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `GEMINI_API_KEY` | `str` | `""` | Google Gemini API key (required for GeminiClient) |
| `GEMINI_MODEL` | `str` | `"gemini-2.0-flash"` | Model name passed to the Gemini SDK |
| `DAILY_LLM_BUDGET` | `float` | `5.00` | Maximum daily spend (USD) before warning |
| `LLM_CACHE_TTL_SECONDS` | `int` | `86400` | Cache TTL in seconds (24 hours) |

## Default Pricing Table

| Model | Input ($/M tokens) | Output ($/M tokens) |
|-------|-------------------|---------------------|
| `gemini-2.0-flash` | $0.10 | $0.40 |
| `gemini-2.5-flash-preview-05-20` | $0.15 | $0.60 |
| `gemini-1.5-flash` | $0.075 | $0.30 |
| `gemini-1.5-pro` | $1.25 | $5.00 |

## Dependencies

| This module uses | This module is used by |
|------------------|----------------------|
| `google-genai` | `services/ai/scoring_service.py` |
| `cachetools` | — |
| `structlog` | — |
| `pydantic` | — |
| `PyYAML` | — |
| `sqlalchemy` (AsyncSession) | — |
| `repositories/llm_request_repository.py` | — |
| `repositories/publication_repository.py` | `services/ai/scoring_service.py` |
| `core/config.py` (Settings) | — |
| `core/prompt_loader.py` (PromptLoader) | `services/ai/scoring_service.py` |
| `core/exceptions.py` (AIServiceError, ValidationError) | — |
| `services/statcan/schemas.py` (CubeMetadataResponse) | `services/ai/scoring_service.py` |

## Architecture Rules Enforced

- **ARCH-DPEN-001**: `GeminiClient`, `LLMCache`, `PromptLoader`, and `BriefGenerationService` receive all dependencies via constructor DI.
- **ARCH-PURA-001**: `LLMCache.build_key()` and `PromptLoader.load()`/`render()` are pure I/O functions (no database, no HTTP).
- **Fault tolerance**: `BriefGenerationService` catches `AIServiceError` per-dataset — one failure never aborts the batch.
- No bare `except:` — only `google.genai.errors.APIError`, `AIServiceError`, `FileNotFoundError`, `KeyError`, `yaml.YAMLError` are caught.
- All functions have full type hints (mypy-compliant).

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
