# Phase 3 Slice 3.3 — Recon (Queue + Shared Shell/Chrome)

## 1) Context confirmation

- `docs/phase-3-slice-3-pre-recon.md` — **missing at expected path**; no alternate file found in this repository. Proceeding from the authoritative findings embedded in the founder prompt for this slice.
- `docs/phase-3-plan.md` — missing at expected path; read at `frontend/docs/phase-3-plan.md`.
- `docs/i18n-glossary.md` — read.
- `docs/I18N_PLAN.md` — read.
- `frontend/lib/l10n/app_en.arb` — read.
- `frontend/lib/l10n/app_ru.arb` — read.
- `backend/` — read in a **scoped probe only** for two questions: `ContentBrief.status` value space and `GET /api/v1/admin/queue` response shape.

State snapshot basis: this recon builds on the authoritative pre-recon findings supplied in the Slice 3.3 prompt (literal inventory/count and queue payload render sites).

## 2) Scope statement

This recon covers only Queue screen literals plus shared shell/chrome literals identified in pre-recon (1 shell literal + 7 queue literals), and produces an ARB key map, RU translations, and EN-kept classifications for Slice 3.4 implementation. Editor, Preview, Graphics, Jobs, KPI, Cubes, and Data Preview are out of scope for this slice. Due to actual literal count being 8 (not 80–140), Slice 3.3 recon and Slice 3.4 implementation are intended to be merged into one implementation PR; this document is the approval gate artifact that would otherwise be a separate PR.

## 3) Scoped backend probe results

### 3.1 — Backend `status` field values

Verbatim source-of-truth enum and model field:

```py
class PublicationStatus(enum.Enum):
    """Lifecycle status of a publication."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
```

```py
status: Mapped[PublicationStatus] = mapped_column(
    Enum(PublicationStatus, name="publication_status"),
    nullable=False,
    default=PublicationStatus.DRAFT,
    server_default="DRAFT",
    index=True,
)
```

Source: `backend/src/models/publication.py:20-25, 88-94`.

One-sentence summary: backend status is constrained enum-backed lifecycle status with valid values `DRAFT` and `PUBLISHED`.

### 3.2 — `GET /api/v1/admin/queue` response shape

Verbatim FastAPI route signature + response model:

```py
@router.get(
    "/queue",
    response_model=list[PublicationResponse],
    status_code=status.HTTP_200_OK,
    summary="List draft publications",
    responses={
        200: {"description": "List of DRAFT publications (may be empty)."},
    },
)
async def get_queue(
    limit: int = Query(default=20, ge=1, le=100),
    pub_repo: PublicationRepository = Depends(_get_repo),
) -> list[PublicationResponse]:
```

Verbatim Pydantic response schema:

```py
class PublicationResponse(BaseModel):
    """Admin-facing publication representation for the queue endpoint.

    Attributes:
        id: Publication primary key.
        headline: Short title of the graphic.
        chart_type: Type of chart (e.g. ``"BAR"``, ``"LINE"``).
        virality_score: AI-estimated virality score (0.0 – 10.0).
        status: Current lifecycle status (``DRAFT`` or ``PUBLISHED``).
        created_at: UTC timestamp of record creation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    headline: str
    chart_type: str
    virality_score: float | None = None
    status: str
    created_at: datetime
```

Sources: `backend/src/api/routers/admin_graphics.py:98-110`; `backend/src/api/schemas/admin_graphics.py:24-44`.

One-sentence summary: `GET /api/v1/admin/queue` returns a **plain list** of `PublicationResponse` objects (no envelope, no `items` key).

## 4) ARB key map (EN + RU, with classification)

| ARB key | EN value | RU value | Placeholders | Plural | Status | Source literal location | Glossary reference |
|---|---|---|---|---|---|---|---|
| errorsAppBootstrapFailed | App bootstrap failed: {error} | Сбой инициализации приложения: {error} | {error}:String | no | NEW (proposed-only; see §6 EN-kept) | frontend/lib/main.dart:70 | glossary §6 `error` → `ошибка` (semantic base); final EN-kept in 3.4 |
| navQueue | Brief Queue | Очередь брифов | — | no | REUSE_EXISTING (`navQueue`) | frontend/lib/features/queue/presentation/queue_screen.dart:22 | existing ARB key (`app_en.arb`/`app_ru.arb`) |
| queueRefreshTooltip | Refresh queue | Обновить очередь | — | no | NEW | frontend/lib/features/queue/presentation/queue_screen.dart:26 | glossary §4 `Refresh` → `Обновить` |
| queueLoadError | Failed to load queue\n{error} | Не удалось загрузить очередь\n{error} | {error}:String | no | NEW | frontend/lib/features/queue/presentation/queue_screen.dart:40 | glossary §5 `Failed` → `Не удалось`; §4 `Refresh` informs queue context |
| commonRetryVerb | Retry | Повторить | — | no | REUSE_EXISTING (`commonRetryVerb`) | frontend/lib/features/queue/presentation/queue_screen.dart:47 | glossary §4 `Try again` → `Повторить`; Appendix C `commonRetryVerb` |
| queueEmptyState | No briefs in queue.\nTap refresh to fetch new ones. | В очереди нет брифов.\nНажмите «Обновить», чтобы загрузить новые. | — | no | NEW | frontend/lib/features/queue/presentation/queue_screen.dart:81 | glossary §4 `Refresh` → `Обновить`; `brief` term requires glossary addition (§7.1) |
| queueRejectVerb | Reject | Отклонить | — | no | NEW | frontend/lib/features/queue/presentation/queue_screen.dart:180 | glossary §4 `Reject` → `Отклонить` |
| queueApproveVerb | Approve | Одобрить | — | no | NEW | frontend/lib/features/queue/presentation/queue_screen.dart:185 | glossary §4 `Approve` → `Одобрить` |

## 5) Backend payload boundary decisions (§3j)

- `brief.viralityScore` (`toStringAsFixed(1)` at queue_screen.dart:132): classify as backend payload numeric value per §3j. Decision: keep in this slice; log debt for locale-aware decimal formatting (`NumberFormat`) because RU decimal comma is preferred UX but non-blocking for Slice 3.4.
- `brief.chartType` (queue_screen.dart:149): classify as EN-kept Category D per §3k (data-viz terminology). Decision: keep EN, no ARB key, aligns with prior data-viz EN-kept policy.
- `brief.headline` (queue_screen.dart:162): classify as backend content payload per §3j. Decision: render as-is; no localization mapping (LLM/user-value content string).
- `brief.status`:
  - Backend model constrains values to enum `DRAFT|PUBLISHED` (`backend/src/models/publication.py:20-25, 88-94`).
  - Queue UI currently does **not** render status anywhere in `queue_screen.dart`.
  - Decision per §3l: defer status ARB mapping until first UI surface that displays status in Queue scope; no speculative `status*` key introduced in this recon.

## 6) EN-kept classification log (§3k)

| Item | Location | Category | Rationale |
|---|---|---|---|
| `_BootstrapError` fallback text `"App bootstrap failed: $error"` | frontend/lib/main.dart:70 | B (dev/diagnostic) | Shown only on bootstrap failure before localized app shell is available; keeping EN is acceptable in this low-frequency diagnostic path for Slice 3.4. |
| `brief.chartType` rendered value | frontend/lib/features/queue/presentation/queue_screen.dart:149 | D (data-viz terminology) | Data-viz family tokens are EN-kept per §3k policy and should not be ARB-localized here. |
| `brief.headline` payload text | frontend/lib/features/queue/presentation/queue_screen.dart:162 | C (machine/content payload) | Backend/LLM content payload is rendered as data, not UI chrome; no client translation boundary per §3j. |

## 7) Glossary / Appendix C proposed updates

### 7.1 — New terms to add to `docs/i18n-glossary.md`

| Proposed section | EN term | Canonical RU | Usage note |
|---|---|---|---|
| §1 Product & entity terms | brief | бриф | Operational object in queue/editor workflow (`Brief Queue`, empty states, cards). |
| §1 Product & entity terms (nav/ops) | queue (noun) | очередь | Use in operational admin context (`Очередь брифов`). |
| §4 Workflow & action terms | Refresh queue | Обновить очередь | Tooltip/button-level phrase for queue reload action; keep imperative voice. |
| §4 Workflow & action terms | Tap refresh to fetch new ones. | Нажмите «Обновить», чтобы загрузить новые. | Empty-state helper sentence; uses RU quotes around button label. |
| §6 Validation & error terms (ops API) | Failed to load queue | Не удалось загрузить очередь | Queue load error prefix with preserved backend detail placeholder. |

### 7.2 — Appendix C (`frontend/docs/phase-3-plan.md`) proposed additions

| Phase 1 / glossary term | Canonical RU | Flutter ARB key |
|---|---|---|
| `queue.refresh.verb` | Обновить очередь | `queueRefreshTooltip` |
| `queue.load.error` | Не удалось загрузить очередь | `queueLoadError` |
| `queue.empty` | В очереди нет брифов.\nНажмите «Обновить», чтобы загрузить новые. | `queueEmptyState` |
| `workflow.reject.verb` | Отклонить | `queueRejectVerb` |
| `workflow.approve.verb` | Одобрить | `queueApproveVerb` |

### 7.3 — `navJobs` retranslation

Founder decision captured for Slice 3.4 application:

- Proposed ARB change: `app_ru.arb` key `navJobs`: `"Задачи"` → `"Задания"`.
- Glossary mirror proposal: add/update nav/domain term `Jobs` → `Задания` (if absent).
- Appendix C mirror proposal: add/update row to keep `navJobs` aligned with glossary canonical RU.

These are proposal-only in this recon doc; implementation lands in Slice 3.4.

## 8) Test plan (for Slice 3.4 implementation)

### 8.1 — Tier 1 widget tests (Queue scope)

- Add `frontend/test/features/queue/presentation/queue_screen_localization_test.dart`.
- EN assertions:
  - Queue app bar title resolves to localized `navQueue` value.
  - Empty-state string resolves to localized `queueEmptyState`.
  - Action buttons render localized `queueRejectVerb` and `queueApproveVerb`.
- RU assertions (same structure):
  - `Очередь брифов`, RU `queueEmptyState`, `Отклонить`, `Одобрить`.
- Where possible assert with `AppLocalizations.of(context)!.<key>` values instead of hardcoded literals (per §3f guidance).

### 8.2 — Tier 2a locale-switch smoke (existing test extension)

- Extend existing `locale_switch_smoke_test.dart` to traverse `/queue`.
- Verify at least 3 queue-specific strings rerender after locale switch EN→RU (e.g., title, refresh tooltip semantics, empty state, or action labels).

### 8.3 — Tier 2b denied-EN shell smoke

- Add/extend RU smoke test for `/queue` ensuring these EN strings are absent in RU mode:
  - `Brief Queue`
  - `Refresh queue`
  - `Reject`
  - `Approve`
  - `No briefs in queue.` (prefix/substring check)
- Allowlist (do not deny in RU mode):
  - `brief.chartType` EN tokens (`LINE`, `BAR`, etc.)
  - `App bootstrap failed: ` diagnostic prefix

### 8.4 — Catalog health (Tier 3)

- Current CI (`.github/workflows/frontend-admin.yml`) runs `flutter test` only; no explicit ARB parity gate detected.
- Slice 3.4 should add/confirm ARB parity check (EN/RU key parity + placeholder parity), either as a dedicated test or CI step.

## 9) Ambiguities / founder questions

Q1. Confirm RU wording for empty-state imperative: keep `Нажмите «Обновить», чтобы загрузить новые.` or prefer a shorter form (`Нажмите «Обновить», чтобы получить новые.`)?

Context: both are idiomatic; `загрузить` aligns better with data-fetch semantics.

Default if no answer: keep `Нажмите «Обновить», чтобы загрузить новые.`

## 10) Deferred literals list (§3l obligation)

None. All in-scope literals are covered by proposed ARB keys (Section 4) or EN-kept classifications (Section 6). No deferrals.

## 11) Plan doc reconciliation

Proposed update for `frontend/docs/phase-3-plan.md` §4 slice table: revise Slice 3.3 `Approx strings` from `80-140` to `8 actual (6 new after reuse)` and note 3.3+3.4 merge due to low literal count; revise Slice 3.4 notes to indicate merged execution with recon-approved key map; add footnote citing `docs/phase-3-slice-3-pre-recon.md` (or the approved recon inventory source) as the recount source.

## 12) Slice 3.4 impl handoff checklist

- [ ] Every ARB key in Section 4 table added to `frontend/lib/l10n/app_en.arb` with `@<key>` metadata.
- [ ] Every ARB key in Section 4 table added to `frontend/lib/l10n/app_ru.arb` with RU value.
- [ ] `flutter gen-l10n` regenerates successfully.
- [ ] `queue_screen.dart` migrated to `AppLocalizations.of(context)!.<key>` for all migrated literals.
- [ ] `main.dart:70` kept EN with `// i18n-kept: category B — see phase-3-slice-3-recon.md Section 6` comment.
- [ ] `navJobs` RU updated from `Задачи` to `Задания` in `app_ru.arb`.
- [ ] Glossary updated per Section 7.1 proposals.
- [ ] Appendix C (`frontend/docs/phase-3-plan.md`) updated per Section 7.2.
- [ ] Plan doc reconciliation from Section 11 applied.
- [ ] Tests per Section 8 added (Tier 1 + 2a extension + 2b).
- [ ] ARB parity CI check confirmed present or added (Section 8.4).
- [ ] Appendix A carryover checklist in `frontend/docs/phase-3-plan.md` fully satisfied.

## 13) Verification commands run

1. `pwd; find .. -name AGENTS.md -print`
   - Purpose: locate repo and scoped agent instructions.
2. `cat docs/phase-3-slice-3-pre-recon.md`
   - Purpose: read authoritative pre-recon snapshot (file missing at path).
3. `cat docs/phase-3-plan.md`
   - Purpose: read phase plan path in prompt (file missing at path).
4. `cat docs/i18n-glossary.md`
   - Purpose: load glossary canon for RU mappings.
5. `find . -maxdepth 3 -type f | rg 'phase-3-slice-3-pre-recon|phase-3-plan|I18N_PLAN|app_en.arb|app_ru.arb|queue_screen.dart|main.dart'`
   - Purpose: locate actual file paths.
6. `find . -maxdepth 4 -type f | rg 'slice-3-pre|slice-3-recon|slice-3'`
   - Purpose: attempt locate pre-recon/recon files by pattern.
7. `cat docs/I18N_PLAN.md`
   - Purpose: read project i18n plan phase context.
8. `cat frontend/docs/phase-3-plan.md`
   - Purpose: read Phase 3 plan at actual path.
9. `cat frontend/lib/l10n/app_en.arb`
   - Purpose: read existing EN ARB keys for reuse checks.
10. `cat frontend/lib/l10n/app_ru.arb`
    - Purpose: read existing RU ARB values for reuse + `navJobs` baseline.
11. `rg -n "class .*ContentBrief|ContentBrief|/api/v1/admin/queue|admin/queue|status" backend -g '!**/__pycache__/**'`
    - Purpose: scoped probe entrypoint for backend `status` and queue route/schema locations.
12. `nl -ba backend/src/api/routers/admin_graphics.py | sed -n '1,220p'`
    - Purpose: capture verbatim queue route signature + response model lines.
13. `nl -ba backend/src/api/schemas/admin_graphics.py | sed -n '1,220p'`
    - Purpose: capture verbatim Pydantic `PublicationResponse` schema.
14. `nl -ba backend/src/models/publication.py | sed -n '1,220p'`
    - Purpose: capture verbatim `PublicationStatus` enum + mapped status field.
15. `nl -ba frontend/lib/features/queue/presentation/queue_screen.dart | sed -n '1,260p'; echo '---'; nl -ba frontend/lib/main.dart | sed -n '40,110p'; echo '---'; rg -n "class ContentBrief|status" frontend/lib/features/queue -g '*.dart'`
    - Purpose: confirm in-scope literal locations and whether `status` is rendered in queue UI.
16. `nl -ba frontend/lib/features/queue/domain/content_brief.dart | sed -n '1,120p'`
    - Purpose: verify Flutter `ContentBrief.status` field presence.
17. `find . -maxdepth 3 -type d | rg '\.github'`
    - Purpose: locate CI workflow directory.
18. `rg -n "arb|l10n|gen-l10n|app_en.arb|app_ru.arb|localization|flutter test" .github/workflows`
    - Purpose: check for ARB parity CI signal.
19. `nl -ba .github/workflows/frontend-admin.yml | sed -n '1,140p'`
    - Purpose: inspect current frontend CI steps.
20. `ls -la docs/phase-3-slice-3-recon.md`
    - Purpose: verify recon file exists on disk.

Command 20 output:

```text
-rw-r--r-- 1 root root 19497 Apr 23 18:23 docs/phase-3-slice-3-recon.md
```
