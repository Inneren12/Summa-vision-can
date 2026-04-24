# Phase 3 Slice 3.11 — Pre-Recon Part A2 (ARB Usage Classification)

> Read-only scan. Classifies every ARB key enumerated in Part A1 §2 (82 keys) into
> one of three buckets: **Rendered** (direct `l10n.X` / `loc.X` call site in `lib/`),
> **Referenced-indirect** (reached only through a mapper / switch), **Dead** (zero
> references anywhere in `lib/`).
> Prerequisite `docs/phase-3-slice-11-pre-recon-part-a1.md` confirmed on disk
> (26 579 B, 357 L). ARB file unchanged since A1 (`@@locale: "en"` still on L2).

## Section 3 — ARB key usage scan

### 3.1 — Scan methodology

**Scope.** `frontend/lib/**/*.dart`, excluding generated files:
- `frontend/lib/l10n/generated/**` (flutter_localizations-generated sources)
- any `*.g.dart` / `*.freezed.dart` (codegen artifacts)

**Primary pattern** (direct render detection):
```
grep -rn "l10n\." frontend/lib/ --include="*.dart" \
  | grep -v "/l10n/generated/" | grep -v "\.g\.dart" | grep -v "\.freezed\.dart"
```
Returned 82 hits across 9 feature/shell files. A parallel scan for the alias
identifier `loc.` (used in `app_drawer.dart` and `language_switcher.dart`) and
for direct `AppLocalizations.of(context)!.<key>` calls (used in `main.dart`)
was also performed.

**Indirect pattern.** For keys with zero direct matches, known mapper files were
inspected individually:
- `frontend/lib/l10n/backend_errors.dart` — `mapBackendErrorCode` switch on `error_code` → 7 error keys.
- `frontend/lib/features/graphics/domain/chart_constants.dart` — `BackgroundCategory.localizedLabel(l10n)` switch → 6 background-category keys.
- Graphics notifier / screen files (`generation_state_notifier.dart`, `generation_notifier.dart`, `preview_screen.dart`, `chart_config_screen.dart`) were scanned for phase → key mappers; **none found** — `generationStatus*` keys are all invoked as direct `l10n.X` calls inside conditional UI branches (see §3.6 anomalies).

**Dead verification.** For each zero-hit key, three additional checks:
1. Full-string grep of the EN value (to catch hard-coded literals).
2. Full-string grep of the RU value.
3. `git log --all --oneline -S<key>` to verify the key was intentionally added.

**Counted exactly once.** `.g.dart`, `.freezed.dart`, and `l10n/generated/` hits are excluded by construction; definition sites inside `backend_errors.dart` and `chart_constants.dart` classify those keys as **Referenced-indirect** (not Rendered).

### 3.2 — Rendered keys (direct `AppLocalizations` call sites in `lib/`)

66 keys. Call sites are cited as `file:line`; where a key is rendered from multiple sites, all are listed.

| # | ARB key | Call sites (file:line) |
|---|---------|------------------------|
| 1 | appTitle | `main.dart:30` (`onGenerateTitle`); `core/routing/app_drawer.dart:32` |
| 2 | navQueue | `core/routing/app_drawer.dart:46` |
| 3 | navCubes | `core/routing/app_drawer.dart:52` |
| 4 | navJobs | `core/routing/app_drawer.dart:58` |
| 5 | navKpi | `core/routing/app_drawer.dart:64` |
| 6 | commonRetryVerb | `features/queue/presentation/queue_screen.dart:48`; `features/graphics/presentation/preview_screen.dart:227`; `features/graphics/presentation/chart_config_screen.dart:804` |
| 7 | commonCancelVerb | `features/graphics/presentation/editable_data_table.dart:88` |
| 8 | languageLabel | `core/shell/language_switcher.dart:29` |
| 9 | languageEnglish | `core/shell/language_switcher.dart:34` |
| 10 | languageRussian | `core/shell/language_switcher.dart:39` |
| 11 | queueTitle | `features/queue/presentation/queue_screen.dart:23` |
| 12 | queueRefreshTooltip | `features/queue/presentation/queue_screen.dart:27` |
| 13 | queueLoadError | `features/queue/presentation/queue_screen.dart:41` |
| 14 | queueEmptyState | `features/queue/presentation/queue_screen.dart:83` |
| 15 | queueRejectVerb | `features/queue/presentation/queue_screen.dart:183` |
| 16 | queueApproveVerb | `features/queue/presentation/queue_screen.dart:188` |
| 17 | editorErrorAppBarTitle | `features/editor/presentation/editor_screen.dart:60` |
| 18 | editorNotFoundAppBarTitle | `features/editor/presentation/editor_screen.dart:72` |
| 19 | editorLoadBriefError | `features/editor/presentation/editor_screen.dart:63` |
| 20 | editorBriefNotFound | `features/editor/presentation/editor_screen.dart:75` |
| 21 | editorEditBriefTitle | `features/editor/presentation/editor_screen.dart:94` |
| 22 | editorResetVerb | `features/editor/presentation/editor_screen.dart:104` |
| 23 | editorViralityScoreLabel | `features/editor/presentation/editor_screen.dart:118` |
| 24 | editorHeadlineLabel | `features/editor/presentation/editor_screen.dart:133` |
| 25 | editorHeadlineHint | `features/editor/presentation/editor_screen.dart:140` |
| 26 | editorBackgroundPromptLabel | `features/editor/presentation/editor_screen.dart:148` |
| 27 | editorBackgroundPromptHint | `features/editor/presentation/editor_screen.dart:156` |
| 28 | editorChartTypeLabel | `features/editor/presentation/editor_screen.dart:165`; `features/graphics/presentation/chart_config_screen.dart:363` |
| 29 | editorPreviewBackgroundButton | `features/editor/presentation/editor_screen.dart:196` |
| 30 | editorGenerateGraphicButton | `features/editor/presentation/editor_screen.dart:213`; `features/graphics/presentation/chart_config_screen.dart:561` |
| 31 | previewAppBarTitle | `features/graphics/presentation/preview_screen.dart:39` |
| 32 | generationStatusSubmitting | `features/graphics/presentation/preview_screen.dart:44`; `features/graphics/presentation/preview_screen.dart:93`; `features/graphics/presentation/chart_config_screen.dart:582` |
| 33 | generationStatusPolling | `features/graphics/presentation/preview_screen.dart:122`; `features/graphics/presentation/chart_config_screen.dart:605` |
| 34 | previewEtaText | `features/graphics/presentation/preview_screen.dart:127` |
| 35 | generationStatusTimeout | `features/graphics/presentation/preview_screen.dart:57`; `features/graphics/presentation/chart_config_screen.dart:185` |
| 36 | generationStatusFailed | `features/graphics/presentation/preview_screen.dart:67`; `features/graphics/presentation/chart_config_screen.dart:180` |
| 37 | previewDownloadButton | `features/graphics/presentation/preview_screen.dart:193` |
| 38 | previewDownloadSaved | `features/graphics/presentation/preview_screen.dart:179`; `features/graphics/presentation/chart_config_screen.dart:717` |
| 39 | previewDownloadFailed | `features/graphics/presentation/preview_screen.dart:186`; `features/graphics/presentation/chart_config_screen.dart:724` |
| 40 | chartConfigAppBarTitle | `features/graphics/presentation/chart_config_screen.dart:163` |
| 41 | chartConfigDataSourceStatcan | `features/graphics/presentation/chart_config_screen.dart:236` |
| 42 | chartConfigDataSourceUpload | `features/graphics/presentation/chart_config_screen.dart:241` |
| 43 | chartConfigCustomDataSectionTitle | `features/graphics/presentation/chart_config_screen.dart:260` |
| 44 | chartConfigDatasetLabel | `features/graphics/presentation/chart_config_screen.dart:326` |
| 45 | chartConfigProductIdLabel | `features/graphics/presentation/chart_config_screen.dart:345` |
| 46 | chartConfigSizePresetLabel | `features/graphics/presentation/chart_config_screen.dart:407` |
| 47 | chartConfigBackgroundCategoryLabel | `features/graphics/presentation/chart_config_screen.dart:458` |
| 48 | chartConfigHeadlineLabel | `features/graphics/presentation/chart_config_screen.dart:509` |
| 49 | chartConfigHeadlineHint | `features/graphics/presentation/chart_config_screen.dart:522` |
| 50 | chartConfigHeadlineRequired | `features/graphics/presentation/chart_config_screen.dart:533` |
| 51 | chartConfigHeadlineMaxChars | `features/graphics/presentation/chart_config_screen.dart:536` |
| 52 | chartConfigEtaRemaining | `features/graphics/presentation/chart_config_screen.dart:619` |
| 53 | chartConfigPublicationChip | `features/graphics/presentation/chart_config_screen.dart:674` |
| 54 | chartConfigVersionChip | `features/graphics/presentation/chart_config_screen.dart:683` |
| 55 | chartConfigDownloadPreviewButton | `features/graphics/presentation/chart_config_screen.dart:731` |
| 56 | chartConfigGenerateAnotherButton | `features/graphics/presentation/chart_config_screen.dart:744` |
| 57 | chartConfigBackToPreviewButton | `features/graphics/presentation/chart_config_screen.dart:761` |
| 58 | chartConfigTryAgainButton | `features/graphics/presentation/chart_config_screen.dart:805` |
| 59 | chartConfigUploadMissingError | `features/graphics/presentation/chart_config_screen.dart:96` |
| 60 | chartConfigUploadPickButton | `features/graphics/presentation/data_upload_widget.dart:144` |
| 61 | chartConfigUploadFileLabel | `features/graphics/presentation/data_upload_widget.dart:150` |
| 62 | chartConfigUploadParseError | `features/graphics/presentation/data_upload_widget.dart:65` |
| 63 | chartConfigUploadSummary | `features/graphics/presentation/data_upload_widget.dart:168` |
| 64 | chartConfigTableShowingRows | `features/graphics/presentation/editable_data_table.dart:60` |
| 65 | chartConfigTableEditCellTitle | `features/graphics/presentation/editable_data_table.dart:79` |
| 66 | commonSaveVerb | `features/graphics/presentation/editable_data_table.dart:92` |

### 3.3 — Referenced-indirect keys (via mappers / switches)

13 keys. All reached through one of two switch mappers; never appear in a direct `l10n.<key>` call site outside the mapper.

| # | ARB key | Mapper location (file:line) | Mapper purpose |
|---|---------|-----------------------------|----------------|
| 1 | errorChartEmptyData | `l10n/backend_errors.dart:16` (case `'CHART_EMPTY_DF'`) | Backend `error_code` → localized message (`mapBackendErrorCode`) |
| 2 | errorChartInsufficientColumns | `l10n/backend_errors.dart:17` (case `'CHART_INSUFFICIENT_COLUMNS'`) | Backend `error_code` → localized message |
| 3 | errorJobUnhandled | `l10n/backend_errors.dart:18` (case `'UNHANDLED_ERROR'`) | Backend `error_code` → localized message |
| 4 | errorJobCoolDown | `l10n/backend_errors.dart:19` (case `'COOL_DOWN_ACTIVE'`) | Backend `error_code` → localized message |
| 5 | errorJobNoHandler | `l10n/backend_errors.dart:20` (case `'NO_HANDLER_REGISTERED'`) | Backend `error_code` → localized message |
| 6 | errorJobIncompatiblePayload | `l10n/backend_errors.dart:21` (case `'INCOMPATIBLE_PAYLOAD_VERSION'`) | Backend `error_code` → localized message |
| 7 | errorJobUnknownType | `l10n/backend_errors.dart:22` (case `'UNKNOWN_JOB_TYPE'`) | Backend `error_code` → localized message |
| 8 | backgroundCategoryHousing | `features/graphics/domain/chart_constants.dart:52` (arm `BackgroundCategory.housing`) | `BackgroundCategory.localizedLabel(l10n)` enum → UI label |
| 9 | backgroundCategoryInflation | `features/graphics/domain/chart_constants.dart:53` (arm `BackgroundCategory.inflation`) | `BackgroundCategory.localizedLabel(l10n)` enum → UI label |
| 10 | backgroundCategoryEmployment | `features/graphics/domain/chart_constants.dart:54` (arm `BackgroundCategory.employment`) | `BackgroundCategory.localizedLabel(l10n)` enum → UI label |
| 11 | backgroundCategoryTrade | `features/graphics/domain/chart_constants.dart:55` (arm `BackgroundCategory.trade`) | `BackgroundCategory.localizedLabel(l10n)` enum → UI label |
| 12 | backgroundCategoryEnergy | `features/graphics/domain/chart_constants.dart:56` (arm `BackgroundCategory.energy`) | `BackgroundCategory.localizedLabel(l10n)` enum → UI label |
| 13 | backgroundCategoryDemographics | `features/graphics/domain/chart_constants.dart:57` (arm `BackgroundCategory.demographics`) | `BackgroundCategory.localizedLabel(l10n)` enum → UI label |

### 3.4 — Dead keys (no references anywhere in `lib/`)

3 keys. Each verified with three independent checks.

| # | ARB key | Evidence of zero runtime reference | Notes |
|---|---------|------------------------------------|-------|
| 1 | commonLoading | `grep -rn "commonLoading" frontend/lib --include="*.dart"` (ex-generated) → **0 matches**. Literal `"Loading..."` / `"Загрузка..."` string grep in Dart source → **0 matches** (loading UX handled via `AsyncValue.loading` branches + `CircularProgressIndicator` in Queue/Editor; Graphics uses `generationStatusSubmitting` / `generationStatusPolling`). Added in 3.2b shell as a common-infra seed. | Reserved / unused common verb. |
| 2 | generationStatusSucceeded | `grep -rn "generationStatusSucceeded" frontend/lib --include="*.dart"` (ex-generated) → **0 matches**. Literal `"Generation completed."` / `"Генерация завершена."` string grep → **0 matches**. Success path on both screens transitions directly to a result view (`_buildResultView` in chart_config_screen, image display in preview_screen) without showing the status label. | Flagged as reserved parity key in Slice 3.8 Fix Round 1 summary; confirmed here. |
| 3 | editorActionError | `grep -rn "editorActionError(" frontend/lib --include="*.dart"` (ex-generated) → **0 matches**. Two textual mentions exist (`editor_notifier.dart:57` and `:61`) but **both are inside a `///` doc comment**, not runtime code. Literal `"Editor action failed: "` / `"Не удалось выполнить действие"` string grep → **0 matches**. | Explicitly reserved per its own doc-comment: _"reserved for future save/publish/unpublish backend actions"_. DEBT-030 mentioned in the `@editorActionError` metadata also references the pending conversion to code-based mapping. |

All three Dead keys were intentionally added (git history present from the feature slice that introduced them); none are stale / garbage.

### 3.5 — Classification summary

| Bucket | Count |
|--------|------:|
| Rendered (direct call site in `lib/`) | **66** |
| Referenced-indirect (via mapper switch) | **13** |
| Dead (zero references in `lib/`) | **3** |
| **Total classified** | **82** |

Matches Part A1 §2 total of **82** keys (✅ parity; every key from A1 appears in exactly one bucket above, no double-classification).

Per-slice cross-cut (slice attribution from A1 §2 ↔ classification bucket):

| Slice | Total | Rendered | Indirect | Dead |
|-------|------:|---------:|---------:|-----:|
| 3.2a/b shell (11) | 11 | 10 | 0 | 1 (`commonLoading`) |
| 3.3+3.4 queue (6) | 6 | 6 | 0 | 0 |
| 3.5+3.6 editor (15) | 15 | 14 | 0 | 1 (`editorActionError`) |
| 3.8 graphics (50) | 50 | 36 | 13 | 1 (`generationStatusSucceeded`) |
| **Total** | **82** | **66** | **13** | **3** |

### 3.6 — Cross-checks

- **Expected 7 `errorCode` indirect references in `backend_errors.dart`:** ✅ confirmed. All 7 arms live on lines 16–22 of `frontend/lib/l10n/backend_errors.dart` inside the `mapBackendErrorCode` switch. 1:1 key coverage (no orphan arm, no orphan key).
- **Expected 6 `backgroundCategory` indirect references in `chart_constants.dart`:** ✅ confirmed. All 6 arms live on lines 52–57 of `frontend/lib/features/graphics/domain/chart_constants.dart` inside `BackgroundCategory.localizedLabel(l10n)`. 1:1 key coverage.
- **Expected 5 `generationStatus*` indirect references via notifier/UI phase mapper:** ⚠ **not confirmed — these keys are Rendered, not Indirect.**
  - Scanned `features/graphics/application/generation_state_notifier.dart`, `features/graphics/domain/generation_notifier.dart`, `features/graphics/presentation/preview_screen.dart`, `features/graphics/presentation/chart_config_screen.dart`. **No phase → ARB-key mapper exists.** The 4 active `generationStatus*` keys are invoked as direct `l10n.<key>` in conditional `if`/`switch`/`when` branches on the notifier's phase enum inside the screen widgets (see §3.2 rows 32, 33, 35, 36).
  - `generationStatusSucceeded` has zero references — classified as **Dead** in §3.4.
  - Net effect on spec hypothesis: expected 18 indirect references (7 + 6 + 5); actual **13** (7 + 6 + 0). The missing 5 are split 4-Rendered + 1-Dead.
- **Any key double-classified:** ❌ no. 66 + 13 + 3 = 82 with no overlap between the three buckets. Manually verified that the 13 indirect keys have zero hits outside their mapper file and that each mapper hit was excluded from the Rendered column.
- **Any key missing from classification:** ❌ no. Every one of the 82 keys listed in Part A1 §2 is present exactly once in §3.2, §3.3, or §3.4.

**Additional anomalies worth flagging for Part B analysis:**
- Call-site multiplicity signal: the heaviest-used keys are `commonRetryVerb` (3 sites), `generationStatusSubmitting` (3 sites), and three 2-site pairs that cross the editor↔chart-config boundary (`editorChartTypeLabel`, `editorGenerateGraphicButton`, `previewDownloadSaved`, `previewDownloadFailed`, plus `generationStatus{Polling,Timeout,Failed}`). These cross-screen shared keys (especially the `editor*` keys rendered by `chart_config_screen`) are candidates for renaming consideration in the recon phase.
- `previewEtaText` is a `preview*`-prefixed key rendered only by `preview_screen.dart`, but its companion ETA label `chartConfigEtaRemaining` is only rendered by `chart_config_screen.dart` — the two ETA labels are not interchangeable (different wording, different placeholder), naming appears intentional.
