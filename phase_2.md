# Phase 2: AI Brain & Visual Engine (Sprint 2 + Pack H)
Здесь мы абстрагируем ИИ, защищаем кошелек кэшированием и настраиваем генерацию векторной графики.

## PR-14 & 47: LLM Interface, Cache & Budget Tracker

```
Role: AI Systems Engineer.
Task: Execute PR-14 and PR-47 for the "Summa Vision" project.
Context (Human): We need a provider-agnostic LLM interface (for Gemini) wrapped in a strict cost-tracking and caching layer to prevent API budget drain.
```

<ac-block id="Ph2-PR14-47-AC1">
**Acceptance Criteria for PR14 & 47 (LLM Interface & Cost Tracker):**
- [ ] Define `LLMInterface` with `generate_text()` and `generate_structured(schema)`.
- [ ] Implement `GeminiClient` satisfying the interface using `google-genai`.
- [ ] Create an `@track_llm_cost` decorator/wrapper. It MUST calculate tokens used, map to a configurable pricing dict, and save the log via `LLMRequestRepository`.
- [ ] **[FIX]** CRITICAL CACHE ARCHITECTURE: Implement LLM Cache. Cache key MUST include BOTH `prompt_hash` AND `data_hash` (hash of the input DataFrame metadata / StatCan cube IDs). If the same prompt is sent but the underlying data has changed (new StatCan release), the cache MUST be invalidated. Cache TTL: 24 hours.
- [ ] Implement Budget Alert: If daily cost exceeds `BaseSettings.DAILY_LLM_BUDGET`, log a `WARNING` via `structlog`.
- [ ] Unit Tests: Send identical prompts with same data_hash twice — assert LLM API called only once. Send same prompt with different data_hash — assert LLM API called twice. Test the budget alert.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/services/ai/llm_interface.py`, `/backend/src/services/ai/cost_tracker.py`, `/backend/src/services/ai/llm_cache.py`
</ac-block>

---

## PR-15: Prompt Config & Extended Schemas

```
Role: AI Prompt Engineer.
Task: Execute PR-15 for the "Summa Vision" project.
Context (Human): Pydantic models for structured outputs and externalizing the System Prompt so non-developers can edit it.
```

<ac-block id="Ph2-PR15-AC1">
**Acceptance Criteria for PR15 (AI Schemas & YAML Prompts):**
- [ ] Create Pydantic model `ContentBrief` (virality_score, headline, bg_prompt).
- [ ] Create Enum `ChartType` MUST include: `LINE`, `BAR`, `SCATTER`, `AREA`, `STACKED_BAR`, `HEATMAP`.
- [ ] CRITICAL ARCHITECTURE: The "Data Journalist" system prompt MUST be loaded from a YAML/JSON configuration file (`/backend/prompts/journalist.yaml`). Do not hardcode the prompt string in Python code.
- [ ] Unit Tests: Test schema validation. Assert the YAML prompt file loads correctly.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/services/ai/schemas.py`, `/backend/src/core/prompt_loader.py`
</ac-block>

---

## PR-16: AI Scoring Service

```
Role: Python Backend Engineer.
Task: Execute PR-16 for the "Summa Vision" project.
Context (Human): Core business logic orchestrating the LLM to score StatCan data for virality.
```

<ac-block id="Ph2-PR16-AC1">
**Acceptance Criteria for PR16 (AI Scoring):**
- [ ] Create `BriefGenerationService` accepting `LLMInterface` via Dependency Injection.
- [ ] Inject raw StatCan metadata into the loaded YAML prompt and call `generate_structured()`.
- [ ] CRITICAL ARCHITECTURE: Save the generated briefs immediately to the database via `PublicationRepository` (status = DRAFT) so they persist between UI reloads.
- [ ] Unit Tests: Mock `LLMInterface` and DB repository. Assert successful DB persistence.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/services/ai/scoring_service.py`
</ac-block>

---

## PR-17: Plotly SVG Visual Engine

```
Role: Data Visualization Engineer.
Task: Execute PR-17 for the "Summa Vision" project.
Context (Human): Render mathematically precise, transparent vector charts. Completely decoupled from AI services.
```

<ac-block id="Ph2-PR17-AC1">
**Acceptance Criteria for PR17 (Plotly Engine):**
- [ ] Implement `generate_chart_svg(df: pd.DataFrame, chart_type: ChartType, size: tuple[int, int] = (1080, 1080)) -> bytes`.
- [ ] **[FIX]** Define size presets as constants:
      - `SIZE_INSTAGRAM = (1080, 1080)`
      - `SIZE_TWITTER = (1200, 628)`
      - `SIZE_REDDIT = (1200, 900)`
      These are the three primary distribution channels. The `size` parameter can accept any custom tuple or one of these presets.
- [ ] CRITICAL ARCHITECTURE: Apply strict styling: `paper_bgcolor='rgba(0,0,0,0)'`, `plot_bgcolor='rgba(0,0,0,0)'`, disable axes grids (`showgrid=False`), use a neon palette.
- [ ] Unit Tests: Pass a mocked DataFrame. Assert output bytes start with `<svg` and contain the specified width/height dimensions. **[FIX]** Test each preset size produces SVG with matching dimensions.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/services/graphics/svg_generator.py`
</ac-block>

---

## PR-18: Image Compositor & Backgrounds

```
Role: Python Graphics Engineer.
Task: Execute PR-18 for the "Summa Vision" project.
Context (Human): Combine the Plotly SVG with an AI-generated background to create the final shareable asset.
```

<ac-block id="Ph2-PR18-AC1">
**Acceptance Criteria for PR18 (Compositor):**
- [ ] Implement `AIImageClient` (mocked implementation for now) returning background `bytes`.
- [ ] **[FIX]** `AIImageClient.generate_background(prompt: str, size: tuple[int, int])` MUST accept a `size` parameter. If the AI returns an image of a different resolution, the compositor MUST resize it to match the target size before compositing.
- [ ] **[FIX]** Implement `composite_image(bg_bytes: bytes, svg_bytes: bytes, dpi: int = 150) -> bytes` using `cairosvg` and `Pillow`. Default DPI is 150 for social media. For B2B high-res licensing (future), callers will pass `dpi=300`.
- [ ] CRITICAL ARCHITECTURE: Add an optional watermark layer (Summa Vision logo text).
- [ ] Unit Tests: MUST include a specific test ensuring that text embedded within the SVG paths does not render as square/tofu artifacts when rasterized by CairoSVG. **[FIX]** Test that output image dimensions match the expected pixel size at the given DPI.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/services/graphics/compositor.py`
</ac-block>

---

## PR-19/20: Async Generation Endpoint (Admin Queue)

```
Role: Python Backend Engineer.
Task: Execute PR-19 and PR-20 for the "Summa Vision" project.
Context (Human): Admin API endpoints for the Flutter command center. Generation takes 20s, so we must use the Task Manager for async polling.
```

<ac-block id="Ph2-PR19-AC1">
**Acceptance Criteria for PR19/20 (Queue & Generate API):**
- [ ] Create router `GET /api/v1/admin/queue` (fetches DRAFT briefs from DB via `PublicationRepository.get_drafts()`).
- [ ] Create router `POST /api/v1/admin/graphics/generate`.
- [ ] CRITICAL ARCHITECTURE: Do NOT block the HTTP response. Use the `TaskManager` (from PR-11/Sprint 1) to submit the generation coroutine (svg -> ai_bg -> composite -> s3_upload).
- [ ] Immediately return `HTTP 202 Accepted` with `{"task_id": "uuid"}`.
- [ ] Ensure generation result updates `PublicationRepository` status to PUBLISHED and saves S3 keys.
- [ ] Unit Tests: Mock the generation pipeline. Verify 202 response and task UUID format.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/api/routers/admin_graphics.py`
</ac-block>
