# Phase 3 Slice 3.11 — Pre-Recon Part A1 (ARB Catalog)

> Read-only inventory. Covers §1 (environment confirmation) and §2 (ARB catalog).
> Successor: Part A2 (usage classification), A3 (switcher/smokes/scripts), B (analysis).

## Section 1 — Environment confirmation

### 1.1 — Fresh read evidence

**`frontend/lib/l10n/app_en.arb`** (395 lines, 17 899 bytes, fresh `cat`):

```json
{
  "@@locale": "en",
  "appTitle": "Summa Vision Admin",
  "@appTitle": {
    "description": "Application title shown in window chrome and admin app shell header"
  },
  "navQueue": "Brief Queue",
  "@navQueue": { "description": "Navigation label for the brief queue screen" },
  "navCubes": "Cubes",
  "@navCubes": { "description": "Navigation label for the StatCan cubes search/detail screens" },
  "navJobs": "Jobs",
  "@navJobs": { "description": "Navigation label for the async jobs monitoring screen" },
  "navKpi": "KPI",
  "@navKpi": { "description": "Navigation label for the KPI monitoring screen" },
  "commonLoading": "Loading...",
  "commonRetryVerb": "Retry",
  "commonCancelVerb": "Cancel",
  "languageLabel": "Language",
  "languageEnglish": "English",
  "languageRussian": "Russian",
  "queueTitle": "Brief Queue",
  "queueRefreshTooltip": "Refresh queue",
  "queueLoadError": "Failed to load queue\n{error}",
  "queueEmptyState": "No briefs in queue.\nTap refresh to fetch new ones.",
  "queueRejectVerb": "Reject",
  "queueApproveVerb": "Approve",
  "editorErrorAppBarTitle": "Editor",
  "editorNotFoundAppBarTitle": "Editor",
  "editorLoadBriefError": "Failed to load brief: {error}",
  "editorBriefNotFound": "Brief not found",
  "editorEditBriefTitle": "Edit Brief #{id}",
  "editorResetVerb": "Reset",
  "editorViralityScoreLabel": "Virality Score",
  "editorHeadlineLabel": "Headline",
  "editorHeadlineHint": "Enter headline...",
  "editorBackgroundPromptLabel": "Background Prompt",
  "editorBackgroundPromptHint": "Describe the AI background image...",
  "editorChartTypeLabel": "Chart Type",
  "editorPreviewBackgroundButton": "Preview Background",
  "editorGenerateGraphicButton": "Generate Graphic",
  "editorActionError": "Editor action failed: {error}",
  "previewAppBarTitle": "Generating Graphic",
  "generationStatusSubmitting": "Submitting generation task...",
  "generationStatusPolling": "Generating... ({current}/{total})",
  "previewEtaText": "This may take up to 2 minutes.",
  "generationStatusTimeout": "Generation timed out.",
  "generationStatusFailed": "Generation failed.",
  "generationStatusSucceeded": "Generation completed.",
  "previewDownloadButton": "Download",
  "previewDownloadSaved": "Saved: {path}",
  "previewDownloadFailed": "Download failed: {error}",
  "chartConfigAppBarTitle": "Chart Configuration",
  "chartConfigDataSourceStatcan": "StatCan Cube",
  "chartConfigDataSourceUpload": "Upload Data",
  "chartConfigCustomDataSectionTitle": "Custom Data",
  "chartConfigDatasetLabel": "Dataset",
  "chartConfigProductIdLabel": "Product ID: {productId}",
  "chartConfigSizePresetLabel": "Size Preset",
  "chartConfigBackgroundCategoryLabel": "Background Category",
  "chartConfigHeadlineLabel": "Chart Headline",
  "chartConfigHeadlineHint": "Enter chart headline...",
  "chartConfigHeadlineRequired": "Headline is required",
  "chartConfigHeadlineMaxChars": "Maximum 200 characters",
  "chartConfigEtaRemaining": "Estimated time remaining: ~{seconds}s",
  "chartConfigPublicationChip": "Publication #{id}",
  "chartConfigVersionChip": "v{version}",
  "chartConfigDownloadPreviewButton": "Download Preview",
  "chartConfigGenerateAnotherButton": "Generate Another",
  "chartConfigBackToPreviewButton": "Back to Preview",
  "chartConfigTryAgainButton": "Try Again",
  "chartConfigUploadMissingError": "Upload a JSON or CSV file first.",
  "chartConfigUploadPickButton": "Upload JSON / CSV",
  "chartConfigUploadFileLabel": "File: {name}",
  "chartConfigUploadParseError": "Failed to parse file: {error}",
  "chartConfigUploadSummary": "{rows} rows × {columns} columns",
  "chartConfigTableShowingRows": "Showing {shown} of {total} rows",
  "chartConfigTableEditCellTitle": "Edit {column} [row {row}]",
  "commonSaveVerb": "Save",
  "backgroundCategoryHousing": "Housing",
  "backgroundCategoryInflation": "Inflation",
  "backgroundCategoryEmployment": "Employment",
  "backgroundCategoryTrade": "Trade",
  "backgroundCategoryEnergy": "Energy",
  "backgroundCategoryDemographics": "Demographics",
  "errorChartEmptyData": "No data to chart.",
  "errorChartInsufficientColumns": "Not enough columns to build the chart.",
  "errorJobUnhandled": "Unexpected error while processing the job.",
  "errorJobCoolDown": "Please wait before starting another generation.",
  "errorJobNoHandler": "Unsupported operation.",
  "errorJobIncompatiblePayload": "Version mismatch between client and server payload.",
  "errorJobUnknownType": "Unknown job type."
}
```

> Note: @<key> metadata blocks (descriptions, placeholders) elided above for readability. Full metadata is preserved verbatim in the source file (395 lines total, 82 value keys + 82 @ metadata blocks + @@locale + closing brace).

**`frontend/lib/l10n/app_ru.arb`** (85 lines, 5 494 bytes, fresh `cat`):

```json
{
  "@@locale": "ru",
  "appTitle": "Summa Vision Admin",
  "navQueue": "Очередь брифов",
  "navCubes": "Кубы",
  "navJobs": "Задания",
  "navKpi": "KPI",
  "commonLoading": "Загрузка...",
  "commonRetryVerb": "Повторить",
  "commonCancelVerb": "Отменить",
  "languageLabel": "Язык",
  "languageEnglish": "English",
  "languageRussian": "Русский",
  "queueTitle": "Очередь брифов",
  "queueRefreshTooltip": "Обновить очередь",
  "queueLoadError": "Не удалось загрузить очередь\n{error}",
  "queueEmptyState": "В очереди нет брифов.\nНажмите «Обновить», чтобы загрузить новые.",
  "queueRejectVerb": "Отклонить",
  "queueApproveVerb": "Одобрить",
  "editorErrorAppBarTitle": "Редактор",
  "editorNotFoundAppBarTitle": "Редактор",
  "editorLoadBriefError": "Не удалось загрузить бриф: {error}",
  "editorBriefNotFound": "Бриф не найден",
  "editorEditBriefTitle": "Редактирование брифа №{id}",
  "editorResetVerb": "Сбросить",
  "editorViralityScoreLabel": "Оценка виральности",
  "editorHeadlineLabel": "Заголовок",
  "editorHeadlineHint": "Введите заголовок...",
  "editorBackgroundPromptLabel": "Промпт фона",
  "editorBackgroundPromptHint": "Опишите желаемое фоновое изображение...",
  "editorChartTypeLabel": "Тип графика",
  "editorPreviewBackgroundButton": "Предпросмотр фона",
  "editorGenerateGraphicButton": "Сгенерировать графику",
  "editorActionError": "Не удалось выполнить действие в редакторе: {error}",
  "previewAppBarTitle": "Генерация графики",
  "generationStatusSubmitting": "Отправка задачи на генерацию...",
  "generationStatusPolling": "Генерация... ({current}/{total})",
  "previewEtaText": "Это может занять до 2 минут.",
  "generationStatusTimeout": "Время генерации истекло.",
  "generationStatusFailed": "Не удалось сгенерировать графику.",
  "generationStatusSucceeded": "Генерация завершена.",
  "previewDownloadButton": "Скачать",
  "previewDownloadSaved": "Сохранено: {path}",
  "previewDownloadFailed": "Не удалось скачать: {error}",
  "chartConfigAppBarTitle": "Настройка графика",
  "chartConfigDataSourceStatcan": "Куб StatCan",
  "chartConfigDataSourceUpload": "Загрузить данные",
  "chartConfigCustomDataSectionTitle": "Пользовательские данные",
  "chartConfigDatasetLabel": "Набор данных",
  "chartConfigProductIdLabel": "ID продукта: {productId}",
  "chartConfigSizePresetLabel": "Формат публикации",
  "chartConfigBackgroundCategoryLabel": "Категория фона",
  "chartConfigHeadlineLabel": "Заголовок графика",
  "chartConfigHeadlineHint": "Введите заголовок графика...",
  "chartConfigHeadlineRequired": "Требуется заголовок",
  "chartConfigHeadlineMaxChars": "Не более 200 символов",
  "chartConfigEtaRemaining": "Оценочное оставшееся время: ~{seconds} c",
  "chartConfigPublicationChip": "Публикация №{id}",
  "chartConfigVersionChip": "v{version}",
  "chartConfigDownloadPreviewButton": "Скачать предпросмотр",
  "chartConfigGenerateAnotherButton": "Сгенерировать ещё",
  "chartConfigBackToPreviewButton": "Назад к предпросмотру",
  "chartConfigTryAgainButton": "Попробовать снова",
  "chartConfigUploadMissingError": "Сначала загрузите файл JSON или CSV.",
  "chartConfigUploadPickButton": "Загрузить JSON / CSV",
  "chartConfigUploadFileLabel": "Файл: {name}",
  "chartConfigUploadParseError": "Не удалось разобрать файл: {error}",
  "chartConfigUploadSummary": "{rows} строк × {columns} столбцов",
  "chartConfigTableShowingRows": "Показано {shown} из {total} строк",
  "chartConfigTableEditCellTitle": "Изменить {column} [строка {row}]",
  "commonSaveVerb": "Сохранить",
  "backgroundCategoryHousing": "Жильё",
  "backgroundCategoryInflation": "Инфляция",
  "backgroundCategoryEmployment": "Занятость",
  "backgroundCategoryTrade": "Торговля",
  "backgroundCategoryEnergy": "Энергетика",
  "backgroundCategoryDemographics": "Демография",
  "errorChartEmptyData": "Нет данных для построения графика.",
  "errorChartInsufficientColumns": "Недостаточно столбцов для построения графика.",
  "errorJobUnhandled": "Непредвиденная ошибка при обработке задания.",
  "errorJobCoolDown": "Подождите перед повторной генерацией.",
  "errorJobNoHandler": "Операция не поддерживается.",
  "errorJobIncompatiblePayload": "Несовместимая версия данных.",
  "errorJobUnknownType": "Неизвестный тип задания."
}
```

**Git state (`git log --oneline -10` + HEAD + branch):**

```
28965fa Merge pull request #143 from Inneren12/claude/fix-error-code-plumbing-TwFBK
8514214 i18n Phase 3 Slice 3.8 Fix Round 3: compile blocker + result hygiene
2594bed i18n Phase 3 Slice 3.8 Fix Round 2: stale errorCode leak across failed runs
0a6f315 i18n Phase 3 Slice 3.8 Fix Round 1: errorCode plumbing + assertion hygiene
8961668 Merge pull request #142 from Inneren12/claude/i18n-phase3-slice38-uqVgf
e2a32b5 i18n Phase 3 Slice 3.8: Preview + Graphics Config + backend error mapper
15fbe51 Add files via upload
c963c2b Merge pull request #141 from Inneren12/codex/implement-slices-3.5-and-3.6
65e513c Fix offstage chart label assertions in editor localization test
7d3e552 Fix editor test localization assertions and import paths

HEAD : 28965fa
Branch: claude/arb-catalog-pre-recon-oW62f
```

**Dart file count (`find frontend/lib -type f -name "*.dart" | wc -l`):** `95`

### 1.2 — Gate check (line-number verification)

| Group | Expected | Actual | EN line range | RU line range | Pass |
|-------|---------:|-------:|---------------|---------------|------|
| `queue*` keys | 6 | 6 | 47–76 (`queueTitle` L47 … `queueApproveVerb` L73) | 14–19 (`queueTitle` L14 … `queueApproveVerb` L19) | ✅ |
| `editor*` keys | 15 | 15 | 77–154 (`editorErrorAppBarTitle` L77 … `editorActionError` L145) | 20–34 (`editorErrorAppBarTitle` L20 … `editorActionError` L34) | ✅ |
| Graphics keys (`preview*` / `chartConfig*` / `backgroundCategory*` / `generationStatus*` / `error*`) | ~46 | 49 (5 + 26 + 6 + 5 + 7) | 155–394 | 35–84 | ✅ (slight +3 vs estimate; `commonSaveVerb` at EN L339 / RU L71 is also a 3.8 adjunct, giving 50 if counted) |
| `navJobs` RU value | `"Задания"` | `"Задания"` (RU L6) | EN L15 | RU L6 | ✅ |
| Total keys EN | ~84 | **82** | — | — | ⚠ 2 fewer than estimate |
| Total keys RU | ~84 | **82** | — | — | ⚠ 2 fewer than estimate |

Gate verdict: **all four structural gates pass**; the ~84 estimate is slightly over-counted — the file actually contains 82 value keys per locale. No key is missing between EN and RU (1-for-1 parity).

### 1.3 — Context file confirmation

| File | Status | Notes |
|------|--------|-------|
| `frontend/docs/phase-3-plan.md` | ✅ present, 42 440 bytes | Not pasted (scope §1 only concerns ARB evidence); confirmed readable via `ls -la`. |
| `frontend/lib/l10n/app_en.arb` | ✅ pasted in 1.1 | 395 lines, 17 899 bytes. |
| `frontend/lib/l10n/app_ru.arb` | ✅ pasted in 1.1 | 85 lines, 5 494 bytes. |
| `frontend/lib/l10n/backend_errors.dart` | ✅ present, 1 200 bytes | Not in §1.3 required list but noted for A2 scope — error-code → ARB-key mapping lives here. |

### 1.4 — Git state

- **Branch:** `claude/arb-catalog-pre-recon-oW62f`
- **HEAD commit:** `28965fa` (Merge PR #143 — Slice 3.8 error-code plumbing fix)
- **Last 10 commits:** see 1.1 block above.
- **Working tree:** clean except for the new doc being written in this task.

## Section 2 — ARB catalog inventory

Single table, one row per ARB value key in `app_en.arb` (excluding `@@locale` and `@<key>` metadata). Values verbatim; embedded literal `\n` sequences preserved as-is (shown as `\n`); values longer than 60 chars truncated with `…` and given a footnote.

Slice-attribution rule (per spec):
- `appTitle`, `nav*`, `common*` (except `commonSaveVerb`), `language*` → **3.2a/b shell**
- `queue*` → **3.3+3.4**
- `editor*` → **3.5+3.6**
- `preview*`, `chartConfig*`, `backgroundCategory*`, `generationStatus*`, `error*`, `commonSaveVerb` → **3.8**

| # | ARB key | EN value | RU value | EN line | RU line | Added in slice | Placeholders | Error code |
|---|---------|----------|----------|--------:|--------:|----------------|:------------:|:----------:|
| 1 | appTitle | Summa Vision Admin | Summa Vision Admin | 3 | 3 | 3.2a shell | no | no |
| 2 | navQueue | Brief Queue | Очередь брифов | 7 | 4 | 3.2a shell | no | no |
| 3 | navCubes | Cubes | Кубы | 11 | 5 | 3.2a shell | no | no |
| 4 | navJobs | Jobs | Задания | 15 | 6 | 3.2a shell | no | no |
| 5 | navKpi | KPI | KPI | 19 | 7 | 3.2a shell | no | no |
| 6 | commonLoading | Loading... | Загрузка... | 23 | 8 | 3.2a shell | no | no |
| 7 | commonRetryVerb | Retry | Повторить | 27 | 9 | 3.2a shell | no | no |
| 8 | commonCancelVerb | Cancel | Отменить | 31 | 10 | 3.2a shell | no | no |
| 9 | languageLabel | Language | Язык | 35 | 11 | 3.2b shell | no | no |
| 10 | languageEnglish | English | English | 39 | 12 | 3.2b shell | no | no |
| 11 | languageRussian | Russian | Русский | 43 | 13 | 3.2b shell | no | no |
| 12 | queueTitle | Brief Queue | Очередь брифов | 47 | 14 | 3.3+3.4 | no | no |
| 13 | queueRefreshTooltip | Refresh queue | Обновить очередь | 51 | 15 | 3.3+3.4 | no | no |
| 14 | queueLoadError | Failed to load queue\n{error} | Не удалось загрузить очередь\n{error} | 55 | 16 | 3.3+3.4 | yes (`error`) | no |
| 15 | queueEmptyState | No briefs in queue.\nTap refresh to fetch new ones. | В очереди нет брифов.\nНажмите «Обновить», чтобы загрузить новые. | 65 | 17 | 3.3+3.4 | no | no |
| 16 | queueRejectVerb | Reject | Отклонить | 69 | 18 | 3.3+3.4 | no | no |
| 17 | queueApproveVerb | Approve | Одобрить | 73 | 19 | 3.3+3.4 | no | no |
| 18 | editorErrorAppBarTitle | Editor | Редактор | 77 | 20 | 3.5+3.6 | no | no |
| 19 | editorNotFoundAppBarTitle | Editor | Редактор | 81 | 21 | 3.5+3.6 | no | no |
| 20 | editorLoadBriefError | Failed to load brief: {error} | Не удалось загрузить бриф: {error} | 85 | 22 | 3.5+3.6 | yes (`error`) | no |
| 21 | editorBriefNotFound | Brief not found | Бриф не найден | 95 | 23 | 3.5+3.6 | no | no |
| 22 | editorEditBriefTitle | Edit Brief #{id} | Редактирование брифа №{id} | 99 | 24 | 3.5+3.6 | yes (`id`:int) | no |
| 23 | editorResetVerb | Reset | Сбросить | 109 | 25 | 3.5+3.6 | no | no |
| 24 | editorViralityScoreLabel | Virality Score | Оценка виральности | 113 | 26 | 3.5+3.6 | no | no |
| 25 | editorHeadlineLabel | Headline | Заголовок | 117 | 27 | 3.5+3.6 | no | no |
| 26 | editorHeadlineHint | Enter headline... | Введите заголовок... | 121 | 28 | 3.5+3.6 | no | no |
| 27 | editorBackgroundPromptLabel | Background Prompt | Промпт фона | 125 | 29 | 3.5+3.6 | no | no |
| 28 | editorBackgroundPromptHint | Describe the AI background image... | Опишите желаемое фоновое изображение... | 129 | 30 | 3.5+3.6 | no | no |
| 29 | editorChartTypeLabel | Chart Type | Тип графика | 133 | 31 | 3.5+3.6 | no | no |
| 30 | editorPreviewBackgroundButton | Preview Background | Предпросмотр фона | 137 | 32 | 3.5+3.6 | no | no |
| 31 | editorGenerateGraphicButton | Generate Graphic | Сгенерировать графику | 141 | 33 | 3.5+3.6 | no | no |
| 32 | editorActionError | Editor action failed: {error} | Не удалось выполнить действие в редакторе: {error} | 145 | 34 | 3.5+3.6 | yes (`error`) | no |
| 33 | previewAppBarTitle | Generating Graphic | Генерация графики | 155 | 35 | 3.8 | no | no |
| 34 | generationStatusSubmitting | Submitting generation task... | Отправка задачи на генерацию... | 159 | 36 | 3.8 | no | no |
| 35 | generationStatusPolling | Generating... ({current}/{total}) | Генерация... ({current}/{total}) | 163 | 37 | 3.8 | yes (`current`:int, `total`:int) | no |
| 36 | previewEtaText | This may take up to 2 minutes. | Это может занять до 2 минут. | 171 | 38 | 3.8 | no | no |
| 37 | generationStatusTimeout | Generation timed out. | Время генерации истекло. | 175 | 39 | 3.8 | no | no |
| 38 | generationStatusFailed | Generation failed. | Не удалось сгенерировать графику. | 179 | 40 | 3.8 | no | no |
| 39 | generationStatusSucceeded | Generation completed. | Генерация завершена. | 183 | 41 | 3.8 | no | no |
| 40 | previewDownloadButton | Download | Скачать | 187 | 42 | 3.8 | no | no |
| 41 | previewDownloadSaved | Saved: {path} | Сохранено: {path} | 191 | 43 | 3.8 | yes (`path`) | no |
| 42 | previewDownloadFailed | Download failed: {error} | Не удалось скачать: {error} | 198 | 44 | 3.8 | yes (`error`) | no |
| 43 | chartConfigAppBarTitle | Chart Configuration | Настройка графика | 205 | 45 | 3.8 | no | no |
| 44 | chartConfigDataSourceStatcan | StatCan Cube | Куб StatCan | 209 | 46 | 3.8 | no | no |
| 45 | chartConfigDataSourceUpload | Upload Data | Загрузить данные | 213 | 47 | 3.8 | no | no |
| 46 | chartConfigCustomDataSectionTitle | Custom Data | Пользовательские данные | 217 | 48 | 3.8 | no | no |
| 47 | chartConfigDatasetLabel | Dataset | Набор данных | 221 | 49 | 3.8 | no | no |
| 48 | chartConfigProductIdLabel | Product ID: {productId} | ID продукта: {productId} | 225 | 50 | 3.8 | yes (`productId`) | no |
| 49 | chartConfigSizePresetLabel | Size Preset | Формат публикации | 232 | 51 | 3.8 | no | no |
| 50 | chartConfigBackgroundCategoryLabel | Background Category | Категория фона | 236 | 52 | 3.8 | no | no |
| 51 | chartConfigHeadlineLabel | Chart Headline | Заголовок графика | 240 | 53 | 3.8 | no | no |
| 52 | chartConfigHeadlineHint | Enter chart headline... | Введите заголовок графика... | 244 | 54 | 3.8 | no | no |
| 53 | chartConfigHeadlineRequired | Headline is required | Требуется заголовок | 248 | 55 | 3.8 | no | no |
| 54 | chartConfigHeadlineMaxChars | Maximum 200 characters | Не более 200 символов | 252 | 56 | 3.8 | no | no |
| 55 | chartConfigEtaRemaining | Estimated time remaining: ~{seconds}s | Оценочное оставшееся время: ~{seconds} c | 256 | 57 | 3.8 | yes (`seconds`:int) | no |
| 56 | chartConfigPublicationChip | Publication #{id} | Публикация №{id} | 263 | 58 | 3.8 | yes (`id`:int) | no |
| 57 | chartConfigVersionChip | v{version} | v{version} | 270 | 59 | 3.8 | yes (`version`) | no |
| 58 | chartConfigDownloadPreviewButton | Download Preview | Скачать предпросмотр | 277 | 60 | 3.8 | no | no |
| 59 | chartConfigGenerateAnotherButton | Generate Another | Сгенерировать ещё | 281 | 61 | 3.8 | no | no |
| 60 | chartConfigBackToPreviewButton | Back to Preview | Назад к предпросмотру | 285 | 62 | 3.8 | no | no |
| 61 | chartConfigTryAgainButton | Try Again | Попробовать снова | 289 | 63 | 3.8 | no | no |
| 62 | chartConfigUploadMissingError | Upload a JSON or CSV file first. | Сначала загрузите файл JSON или CSV. | 293 | 64 | 3.8 | no | no |
| 63 | chartConfigUploadPickButton | Upload JSON / CSV | Загрузить JSON / CSV | 297 | 65 | 3.8 | no | no |
| 64 | chartConfigUploadFileLabel | File: {name} | Файл: {name} | 301 | 66 | 3.8 | yes (`name`) | no |
| 65 | chartConfigUploadParseError | Failed to parse file: {error} | Не удалось разобрать файл: {error} | 308 | 67 | 3.8 | yes (`error`) | no |
| 66 | chartConfigUploadSummary | {rows} rows × {columns} columns | {rows} строк × {columns} столбцов | 315 | 68 | 3.8 | yes (`rows`:int, `columns`:int) | no |
| 67 | chartConfigTableShowingRows | Showing {shown} of {total} rows | Показано {shown} из {total} строк | 323 | 69 | 3.8 | yes (`shown`:int, `total`:int) | no |
| 68 | chartConfigTableEditCellTitle | Edit {column} [row {row}] | Изменить {column} [строка {row}] | 331 | 70 | 3.8 | yes (`column`, `row`:int) | no |
| 69 | commonSaveVerb | Save | Сохранить | 339 | 71 | 3.8 | no | no |
| 70 | backgroundCategoryHousing | Housing | Жильё | 343 | 72 | 3.8 | no | no |
| 71 | backgroundCategoryInflation | Inflation | Инфляция | 347 | 73 | 3.8 | no | no |
| 72 | backgroundCategoryEmployment | Employment | Занятость | 351 | 74 | 3.8 | no | no |
| 73 | backgroundCategoryTrade | Trade | Торговля | 355 | 75 | 3.8 | no | no |
| 74 | backgroundCategoryEnergy | Energy | Энергетика | 359 | 76 | 3.8 | no | no |
| 75 | backgroundCategoryDemographics | Demographics | Демография | 363 | 77 | 3.8 | no | no |
| 76 | errorChartEmptyData | No data to chart. | Нет данных для построения графика. | 367 | 78 | 3.8 | no | yes (`CHART_EMPTY_DF`) |
| 77 | errorChartInsufficientColumns | Not enough columns to build the chart. | Недостаточно столбцов для построения графика. | 371 | 79 | 3.8 | no | yes (`CHART_INSUFFICIENT_COLUMNS`) |
| 78 | errorJobUnhandled | Unexpected error while processing the job. | Непредвиденная ошибка при обработке задания. | 375 | 80 | 3.8 | no | yes (`UNHANDLED_ERROR`) |
| 79 | errorJobCoolDown | Please wait before starting another generation. | Подождите перед повторной генерацией. | 379 | 81 | 3.8 | no | yes (`COOL_DOWN_ACTIVE`) |
| 80 | errorJobNoHandler | Unsupported operation. | Операция не поддерживается. | 383 | 82 | 3.8 | no | yes (`NO_HANDLER_REGISTERED`) |
| 81 | errorJobIncompatiblePayload | Version mismatch between client and server payload. | Несовместимая версия данных. | 387 | 83 | 3.8 | no | yes (`INCOMPATIBLE_PAYLOAD_VERSION`) |
| 82 | errorJobUnknownType | Unknown job type. | Неизвестный тип задания. | 391 | 84 | 3.8 | no | yes (`UNKNOWN_JOB_TYPE`) |

### Section 2 summary

- **Total rows:** 82 ARB value keys (per locale; EN and RU are 1-for-1).
- **By slice breakdown:**
  - 3.2a/b shell: **11** (rows 1–11)
  - 3.3+3.4 queue: **6** (rows 12–17)
  - 3.5+3.6 editor: **15** (rows 18–32)
  - 3.8 graphics (incl. `commonSaveVerb` and `backgroundCategory*`): **50** (rows 33–82)
- **Placeholder-bearing keys:** **16** — `queueLoadError`, `editorLoadBriefError`, `editorEditBriefTitle`, `editorActionError`, `generationStatusPolling`, `previewDownloadSaved`, `previewDownloadFailed`, `chartConfigProductIdLabel`, `chartConfigEtaRemaining`, `chartConfigPublicationChip`, `chartConfigVersionChip`, `chartConfigUploadFileLabel`, `chartConfigUploadParseError`, `chartConfigUploadSummary`, `chartConfigTableShowingRows`, `chartConfigTableEditCellTitle`.
- **Error-code keys (`errorChart*` / `errorJob*`):** **7** (rows 76–82). Error codes: `CHART_EMPTY_DF`, `CHART_INSUFFICIENT_COLUMNS`, `UNHANDLED_ERROR`, `COOL_DOWN_ACTIVE`, `NO_HANDLER_REGISTERED`, `INCOMPATIBLE_PAYLOAD_VERSION`, `UNKNOWN_JOB_TYPE`.
- **Anomalies:**
  - Total is **82**, two fewer than the spec's ~84 estimate — likely a rounding in the estimate, not a missing key. EN↔RU parity is exact (82/82, no orphan keys either way).
  - Two EN duplicate values with distinct keys, by design: `queueTitle` == `navQueue` ("Brief Queue") and `editorErrorAppBarTitle` == `editorNotFoundAppBarTitle` ("Editor") — the ARB descriptions explicitly flag these as intentional per §3l migration rule (kept separate to allow divergent tuning).
  - `chartConfigEtaRemaining` RU has ` c` (space + Cyrillic "с") where EN has `s` (no space) — per-locale stylistic difference, not a defect.
  - `languageEnglish` RU value is `"English"` (Latin, endonym convention) while `languageRussian` RU value is `"Русский"` (Cyrillic endonym) — intentional switcher convention.
