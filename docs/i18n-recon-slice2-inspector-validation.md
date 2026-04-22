# i18n Recon — Slice 2: Inspector + Validation

Date: 2026-04-22
Scope: Inspector, RightRail, validation layer
Status: RECON COMPLETE
Previous slice: Slice 1 merged — next-intl infrastructure in place

## 1. Files audited

| File | Found | Hardcoded strings | Component type | Notes |
|---|---|---|---|---|
| frontend-public/src/components/editor/components/Inspector.tsx | yes | 15 | Client | Main Inspector UI; contains labels, empty-state copy, toggles, and badge abbreviations. |
| frontend-public/src/components/editor/components/RightRail.tsx | yes | 4 | Client | Tab labels + ARIA tablist label. |
| frontend-public/src/components/editor/components/Inspector/**/*.tsx | no | 0 | — | No nested Inspector subdirectory found. |
| frontend-public/src/components/editor/components/RightRail/**/*.tsx | no | 0 | — | No nested RightRail subdirectory found. |
| frontend-public/src/components/editor/validation/block-data.ts | yes | 29 | Module (non-component) | Validation return messages include many user-visible errors; mix of static and interpolated literals. |
| frontend-public/src/components/editor/validation/contrast.ts | yes | 3 | Module (non-component) | Contrast issue formatter returns interpolated user-visible message. |
| frontend-public/src/components/editor/validation/invariants.ts | yes | 6 | Module (non-component) | Integrity violation messages are string templates. |
| frontend-public/src/components/editor/validation/validate.ts | yes | 25 | Module (non-component) | Primary validation aggregator; many message templates flow directly to QA UI. |
| frontend-public/src/components/editor/components/QAPanel.tsx *(discovered)* | yes | 3 | Client | Discovered related file rendering validation output (`vr.errors/warnings/info`). |
| frontend-public/src/components/editor/components/TopBar.tsx *(discovered)* | yes | 14 | Client | Discovered related file exposing validation state in export tooltip and action labels. |
| frontend-public/src/components/editor/components/ReviewPanel.tsx *(discovered via RightRail)* | yes | 35 | Client | Not validation-core, but in RightRail scope and full of user-visible strings. |

## 2. Hardcoded strings inventory

### frontend-public/src/components/editor/components/Inspector.tsx

| # | String (EN) | Location (line ~N) | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | `"REQ·🔒"` | ~24 | Required+locked badge label | inspector.badge.required_locked | partial | Требуемый · 🔒 (TBD exact compact form) |
| 2 | `"REQ"` | ~24 | Required+editable badge label | inspector.badge.required_editable | partial | Обязательный (short form TBD) |
| 3 | `"OPT·ON"` | ~24 | Optional default badge | inspector.badge.optional_default | new | TBD |
| 4 | `"OPT"` | ~24 | Optional available badge | inspector.badge.optional_available | new | TBD |
| 5 | `"Inspector"` | ~90 | Panel title | inspector.title | covered | инспектор |
| 6 | `"TPL"` | ~91 | Template mode marker | inspector.template_mode.short | new | TBD |
| 7 | `"Select a block"` | ~94 | Empty state | inspector.empty.select_block | covered | Выберите блок |
| 8 | `"from Blocks tab"` | ~94 | Empty state continuation | inspector.empty.from_blocks_tab | partial | из вкладки «Блоки» (TBD casing/quotes) |
| 9 | `"HIDDEN"` | ~100 | Hidden block marker | inspector.hidden.status | partial | Скрыт |
| 10 | `"Contrast"` | ~106 | Contrast section header | validation.contrast.title | partial | Контраст |
| 11 | `" (gradient)"` | ~112 | Contrast issue suffix | validation.contrast.gradient_suffix | partial | (градиент) |
| 12 | `"✓ On"` | ~133 | Toggle ON label | common.toggle.on | partial | ✓ Вкл |
| 13 | `"○ Off"` | ~133 | Toggle OFF label | common.toggle.off | partial | ○ Выкл |
| 14 | `"TYPE"` | ~146 | Debug metadata label | inspector.meta.type | new | TBD |
| 15 | `"STATUS"`, `"SECTIONS"`, `"MAX"` | ~146-147 | Debug metadata labels | inspector.meta.status / sections / max | partial | Статус / Разделы / Макс. |

### frontend-public/src/components/editor/components/RightRail.tsx

| # | String (EN) | Location (line ~N) | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | `"Right rail"` | ~102 | `aria-label` for tablist | right_rail.aria_label | new | TBD |
| 2 | `"Inspector"` | ~117 | Tab label | inspector.title | covered | инспектор |
| 3 | `"Review"` | ~131 | Tab label | review.title | covered | Проверка |
| 4 | `"inspector"`, `"review"` | ~22-23,48 | Tab IDs/state values (UI-coupled) | right_rail.tab.inspector / review | partial | инспектор / проверка |

### frontend-public/src/components/editor/validation/block-data.ts

| # | String (EN) | Location (line ~N) | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | `"items must be an array"` | ~49,118,176 | Validation error | validation.items.array_required | partial | Поле items должно быть массивом |
| 2 | `"at least one item required"` | ~52,178 | Validation error | validation.items.min_one | partial | Требуется хотя бы один элемент |
| 3 | `` `too many items: ${props.items.length} (max 30)` `` | ~55 | Validation error (interpolated) | validation.items.too_many | partial | Слишком много элементов: {count} (макс. 30) |
| 4 | `` `item[${i}]: label must be non-empty string` `` | ~59,182 | Validation error (interpolated) | validation.item.label_required | partial | item[{index}]: label должно быть непустой строкой |
| 5 | `` `item[${i}]: value must be a finite number` `` | ~62 | Validation error | validation.item.value_finite | partial | item[{index}]: value должно быть конечным числом |
| 6 | `"showBenchmark is true but benchmarkValue is not a finite number"` | ~70 | Validation error | validation.benchmark.value_finite_when_enabled | new | TBD |
| 7 | `"series must be an array"` | ~81 | Validation error | validation.series.array_required | partial | Поле series должно быть массивом |
| 8 | `"xLabels must be an array"` | ~84 | Validation error | validation.xlabels.array_required | new | TBD |
| 9 | `"at least one series required"` | ~86 | Validation error | validation.series.min_one | partial | Требуется хотя бы один ряд |
| 10 | `"xLabels cannot be empty"` | ~87 | Validation error | validation.xlabels.non_empty | new | TBD |
| 11 | `"all xLabels must be non-empty strings"` | ~89 | Validation error | validation.xlabels.all_non_empty | new | TBD |
| 12 | `` `series[${i}]: label must be non-empty string` `` | ~94 | Validation error | validation.series.label_required | partial | series[{index}]: label должно быть непустой строкой |
| 13 | `` `series[${i}]: role must be one of ${VALID_SERIES_ROLES.join(', ')}` `` | ~97 | Validation error | validation.series.role_invalid | partial | series[{index}]: role должен быть одним из {roles} |
| 14 | `` `series[${i}]: data must be an array` `` | ~100 | Validation error | validation.series.data_array_required | partial | series[{index}]: data должно быть массивом |
| 15 | `` `series[${i}] "${s.label}": ${s.data.length} points but ${props.xLabels.length} xLabels` `` | ~104 | Validation error | validation.series.points_mismatch | new | TBD |
| 16 | `` `series[${i}] "${s.label}": contains non-finite values` `` | ~107 | Validation error | validation.series.non_finite_values | partial | ... содержит неконечные значения |
| 17 | `"at least 2 KPI items required"` | ~120 | Validation error | validation.kpi.min_two | partial | Требуется не менее 2 KPI-элементов |
| 18 | `` `too many items: ${props.items.length} (max 4)` `` | ~121 | Validation error | validation.kpi.max_items | partial | Слишком много элементов: {count} (макс. 4) |
| 19 | `` `kpi[${i}]: label must be non-empty string` `` | ~125 | Validation error | validation.kpi.label_required | partial | ... |
| 20 | `` `kpi[${i}]: value must be non-empty string` `` | ~128 | Validation error | validation.kpi.value_required | partial | ... |
| 21 | `` `kpi[${i}]: delta must be string` `` | ~131 | Validation error | validation.kpi.delta_string | partial | ... |
| 22 | `` `kpi[${i}]: direction must be one of ${VALID_DIRECTIONS.join(', ')}` `` | ~134 | Validation error | validation.kpi.direction_invalid | partial | ... |
| 23 | `"columns must be an array"` | ~145 | Validation error | validation.table.columns_array_required | partial | Столбцы должны быть массивом |
| 24 | `"rows must be an array"` | ~148 | Validation error | validation.table.rows_array_required | partial | Строки должны быть массивом |
| 25 | `"at least 2 columns required"` | ~150 | Validation error | validation.table.columns_min_two | partial | Требуется минимум 2 столбца |
| 26 | `"at least one row required"` | ~151 | Validation error | validation.table.rows_min_one | partial | Требуется хотя бы одна строка |
| 27 | `` `row[${i}]: country must be non-empty string` `` | ~155 | Validation error | validation.row.country_required | covered | row[{index}]: country должно быть непустой строкой |
| 28 | `` `row[${i}]: rank must be a finite number` `` | ~158 | Validation error | validation.row.rank_finite | partial | ... |
| 29 | `` `row[${i}]: ${r.vals.length} vals but ${props.columns.length - 1} data columns` `` | ~165 | Validation error | validation.row.vals_count_mismatch | new | TBD |

### frontend-public/src/components/editor/validation/contrast.ts

| # | String (EN) | Location (line ~N) | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | `` `Invalid hex colour: ${hex}` `` | ~120 | Parser error | validation.color.invalid_hex | partial | Неверный hex-цвет: {hex} |
| 2 | `` `${block.type}.${slot}: contrast ${ratio.toFixed(2)}:1 below ${threshold}:1 on ${bgMeta.base}` `` | ~196 | Contrast error message | validation.contrast.below_threshold_base | partial | ... контраст {ratio}:1 ниже {threshold}:1 на {bg} |
| 3 | `` `${block.type}.${slot}: contrast ${ratio.toFixed(2)}:1 below ${threshold}:1 on ${bgMeta.lightestStop}` `` | ~215 | Contrast warning message | validation.contrast.below_threshold_gradient | partial | ... |

### frontend-public/src/components/editor/validation/invariants.ts

| # | String (EN) | Location (line ~N) | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | `` `Section "${sec.id}" references missing block "${bid}"` `` | ~28 | Integrity violation | validation.integrity.dangling_ref | partial | Раздел "{sectionId}" ссылается на отсутствующий блок "{blockId}" |
| 2 | `` `Block "${bid}" referenced by multiple sections` `` | ~35 | Integrity violation | validation.integrity.duplicate_ref | partial | Блок "{blockId}" используется в нескольких разделах |
| 3 | `` `Block "${bid}" not referenced by any section` `` | ~48 | Integrity violation | validation.integrity.orphan_block | partial | Блок "{blockId}" не привязан ни к одному разделу |
| 4 | `` `Required block type "${reqType}" not found` `` | ~61 | Integrity violation | validation.integrity.required_block_missing | partial | Требуемый тип блока "{type}" не найден |
| 5 | `` `Unknown block type: "${block.type}"` `` | ~76 | Integrity violation | validation.integrity.unknown_block_type | partial | Неизвестный тип блока: "{type}" |
| 6 | `` `Block "${reg.name}" in "${sec.type}" section (allowed: ${reg.allowedSections.join(', ')})` `` | ~84 | Integrity violation | validation.integrity.wrong_section | partial | ... |

### frontend-public/src/components/editor/validation/validate.ts

| # | String (EN) | Location (line ~N) | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | `` `Unknown palette: "${doc.page.palette}"` `` | ~18 | Error | validation.page.unknown_palette | partial | Неизвестная палитра: "{palette}" |
| 2 | `` `Unknown background: "${doc.page.background}"` `` | ~19 | Error | validation.page.unknown_background | partial | Неизвестный фон: "{background}" |
| 3 | `` `Unknown size: "${doc.page.size}"` `` | ~20 | Error | validation.page.unknown_size | partial | Неизвестный размер: "{size}" |
| 4 | `` `${BREG[req].name} present` `` | ~24 | Pass message | validation.required_block.present | partial | {blockName} присутствует |
| 5 | `` `${BREG[req].name} is required` `` | ~25 | Error | validation.required_block.missing | partial | {blockName} обязателен |
| 6 | `"Headline is empty"` | ~29 | Error | validation.headline.empty | covered | Заголовок пуст |
| 7 | `"Hero number is empty"` | ~31 | Error | validation.hero_number.empty | partial | Число hero-блока пусто |
| 8 | `` `${reg.name}: ${txt.length}/${mx} OVERFLOW` `` | ~33 | Error | validation.max_chars.overflow | partial | ... ПЕРЕПОЛНЕНИЕ |
| 9 | `` `${reg.name}: ${txt.length}/${mx} chars` `` | ~33 | Warning | validation.max_chars.near_limit | partial | ... символов |
| 10 | `` `${reg.name}: ${lines}/${reg.cst.maxLines} lines` `` | ~34 | Warning | validation.max_lines.near_limit | partial | ... строк |
| 11 | `` `Duplicate section id: "${sec.id}"` `` | ~44 | Error | validation.section.duplicate_id | partial | Дублирующийся id раздела: "{id}" |
| 12 | `` `Section "${sec.id}" has duplicate blockId: "${bid}"` `` | ~51 | Error | validation.section.duplicate_block_id | partial | ... |
| 13 | `` `${reg.name} not allowed in ${sec.type}` `` | ~60 | Error | validation.section.block_not_allowed | partial | ... |
| 14 | `` `${reg.name}: ${c}x in ${sec.type} (max ${reg.maxPerSection})` `` | ~63 | Warning | validation.section.max_per_section | partial | ... |
| 15 | `` `${name}: ${err}` `` | ~73 | Error wrapper | validation.block_data.prefixed_error | partial | {name}: {error} |
| 16 | `` `Ranked Bars: ${n} items — may be dense` `` | ~83 | Warning | validation.density.ranked_bars_dense | new | TBD |
| 17 | `"Ranked Bars: too many items for this canvas height"` | ~84 | Warning | validation.density.ranked_bars_height | new | TBD |
| 18 | `` `Line Chart: ${xl} x-labels — may overlap` `` | ~88 | Warning | validation.density.line_chart_overlap | partial | ... |
| 19 | `"KPI Compare: more than 4 items may be cramped"` | ~92 | Warning | validation.density.kpi_compare_cramped | new | TBD |
| 20 | `` `Visual Table: ${n} rows — may overflow on ${sz.n}` `` | ~96 | Warning | validation.density.visual_table_overflow | new | TBD |
| 21 | `"Small Multiples: more than 9 cells may be too dense"` | ~100 | Warning | validation.density.small_multiples_dense | new | TBD |
| 22 | `` `Headline ${len} chars — shorter may work better` `` | ~108 | Info | validation.layout.headline_shorter | partial | ... |
| 23 | `` `Headline line ${longest} chars — may overflow small sizes` `` | ~111 | Warning | validation.layout.headline_line_overflow | partial | ... |
| 24 | `"Source is still default"` | ~115 | Warning | validation.source_footer.default_text | partial | Источник всё ещё по умолчанию |
| 25 | `"Annotation may not fit on landscape sizes"` / `"Visual Table may be cramped on narrow canvas"` / `"Annotation block is empty"` / `` `Section "${sec.sectionType}" may overflow: ~${...}px used / ${...}px available` `` | ~117-121,130 | Info/warnings | validation.layout.annotation_landscape / table_narrow / annotation_empty / section_overflow | partial | TBD nuanced phrasing |

### frontend-public/src/components/editor/components/QAPanel.tsx *(discovered)*

| # | String (EN) | Location (line ~N) | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | `"Expand QA panel"` | ~20 | `aria-label` | qa.expand.aria | partial | Развернуть панель QA |
| 2 | `"QA"` / `"QA mode"` | ~20,27,28 | Labels/ARIA | qa.title / qa.mode.aria | new | TBD |
| 3 | `"draft"`, `"publish"` | ~29 | Mode tabs | workflow.draft.status / publish.verb_or_status | covered | черновик / опубликовать |

### frontend-public/src/components/editor/components/TopBar.tsx *(discovered)*

| # | String (EN) | Location (line ~N) | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | `` `Export disabled: ${errs} validation error${errs === 1 ? '' : 's'}` `` | ~67 | Export tooltip | export.disabled.validation_errors | partial | Экспорт отключён: {count} ошибок валидации |
| 2 | `"Export disabled: loading fonts…"` | ~69 | Export tooltip | export.disabled.loading_fonts | new | TBD |
| 3 | `"Export as PNG"` | ~70,118 | Export label/ARIA | export.png.verb | partial | Экспортировать в PNG |
| 4 | `"Editor mode"` | ~79 | `aria-label` | editor.mode.aria | covered | режим редактора |
| 5 | `` `Switch to ${m} mode` `` | ~80 | Mode button aria | editor.mode.switch_to | partial | Переключиться в режим {mode} |
| 6 | `"Undo"` / `"Undo (Ctrl+Z)"` | ~83 | Aria/title | undo.verb / undo.shortcut | covered | Отменить |
| 7 | `"Redo"` / `"Redo (Ctrl+Y)"` | ~84 | Aria/title | redo.verb / redo.shortcut | covered | Повторить |
| 8 | `` `${errs}err ${warns}warn` `` | ~89 | Validation summary tooltip | qa.summary.compact | new | TBD |
| 9 | `"Disable debug overlay"` / `"Enable debug overlay"` | ~95 | Debug aria | debug.overlay.disable / enable | new | TBD |
| 10 | `"Debug overlay ON (Ctrl+Shift+D)"` / `"Debug overlay OFF (Ctrl+Shift+D)"` | ~96 | Debug title | debug.overlay.on / off | new | TBD |
| 11 | `"Import document from JSON"` | ~111 | Import button aria/title | import.document_json | partial | Импорт документа из JSON |
| 12 | `"Export document as JSON"` | ~112 | Export JSON aria/title | export.document_json | partial | Экспорт документа в JSON |
| 13 | `"Save draft (unsaved changes)"` / `"Save draft (no changes)"` | ~113 | Save button aria | draft.save.unsaved / unchanged | partial | Сохранить черновик (...) |
| 14 | `"Save (Ctrl+S)"`, `"IMPORT"`, `"JSON"`, `"SAVE"`, `"EXPORT"` | ~111-121 | Action labels | save.shortcut / import.noun-or-verb / etc. | covered | Сохранить / Импорт / Экспорт |

### frontend-public/src/components/editor/components/ReviewPanel.tsx *(discovered via RightRail)*

| # | String (EN) | Location (line ~N) | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | `"→ In review"` / `"→ Approved"` / `"→ Draft"` / `"→ Exported"` / `"→ Published"` | ~40-69 | Workflow transition button labels | review.transition.* | partial | → На проверке / Одобрено / Черновик / Экспортировано / Опубликовано |
| 2 | `"Request changes"` / `"Return to draft"` | ~50,58 | Note modal titles | review.request_changes.title / review.return_to_draft.title | partial | Запросить изменения / Вернуть в черновик |
| 3 | `` `Add comment on ${blockLabel}` `` | ~123 | Modal title (interpolated) | review.comment.add_on_block | partial | Добавить комментарий к {block} |
| 4 | `"Comment"` / `"Add"` / `"Type your comment..."` | ~124-127 | Comment modal labels | review.comment.label / add / placeholder | partial | Комментарий / Добавить / Введите комментарий... |
| 5 | `"Reply to comment"` / `"Reply"` / `"Type your reply..."` | ~136-140 | Reply modal strings | review.reply.* | partial | Ответить на комментарий / Ответ / Введите ответ... |
| 6 | `"Edit comment"` / `"Save"` | ~149,153 | Edit modal strings | review.comment.edit / save | covered | Редактировать комментарий / Сохранить |
| 7 | `"Note (optional)"` / `"Confirm"` / `"Optional context for this transition..."` | ~167-170 | Transition note modal | review.note.optional / confirm / placeholder | partial | Примечание (необязательно) / Подтвердить / ... |
| 8 | `"Duplicate as draft"` | ~239 | Transition action | review.transition.duplicate_as_draft | partial | Дублировать как черновик |
| 9 | `"No transitions available"` | ~251 | Empty state | review.transitions.empty | partial | Нет доступных переходов |
| 10 | `` `Threads (${visibleThreads.length})` `` | ~285 | Section title | review.threads.title_count | partial | Треды ({count}) |
| 11 | `"Show resolved"` | ~304 | Toggle label | review.threads.show_resolved | partial | Показать решённые |
| 12 | `"No threads to show."` | ~316 | Empty state | review.threads.empty | partial | Нет тредов для показа |
| 13 | `` `On ${blockDisplayLabel(...)}` `` | ~350 | Add-comment context label | review.comment.on_block | partial | На {block} |
| 14 | `"Add comment"` | ~356,360 | Button + title | review.comment.add | partial | Добавить комментарий |
| 15 | `` `History (${history.length})` `` | ~392 | History header | review.history.title_count | partial | История ({count}) |
| 16 | `"Collapse"` / `` `Show all ${history.length}` `` | ~410-411 | History toggle | review.history.collapse / show_all | partial | Свернуть / Показать все {count} |
| 17 | `"No events yet."` | ~424 | History empty state | review.history.empty | partial | Событий пока нет |
| 18 | `"Reply to thread"` / `"Reply"` | ~591,595 | Thread reply control | review.reply.to_thread / reply | partial | Ответить в тред / Ответить |
| 19 | `"Comment deleted"` | ~637 | Tombstone text | review.comment.deleted | partial | Комментарий удалён |
| 20 | `" (edited)"` / `"Resolved"` | ~669-680 | Comment metadata/status | review.comment.edited_suffix / resolved | partial | (изменён) / Решено |
| 21 | `"Reopen"` / `"Resolve"` / `"Edit"` / `"Delete"` | ~701-739 | Comment action buttons | review.comment.reopen/resolve/edit/delete | covered | Переоткрыть / Решить / Редактировать / Удалить |

## 3. Validation-specific patterns

### Interpolated messages

| File | Pattern | Suggested ICU-style key |
|---|---|---|
| validation/validate.ts | `` `${BREG[req].name} is required` `` / `` `${BREG[req].name} present` `` | `validation.required_block.{missing|present}` with `{blockName}` |
| validation/validate.ts | `` `${reg.name}: ${txt.length}/${mx} OVERFLOW` `` | `validation.max_chars.overflow` with `{blockName}`, `{count}`, `{max}` |
| validation/validate.ts | `` `Section "${sec.sectionType}" may overflow: ~${...}px used / ${...}px available` `` | `validation.layout.section_overflow` with `{sectionType}`, `{usedPx}`, `{availablePx}` |
| validation/block-data.ts | `` `series[${i}] "${s.label}": ${s.data.length} points but ${props.xLabels.length} xLabels` `` | `validation.series.points_mismatch` with `{index}`, `{label}`, `{points}`, `{xLabels}` |
| validation/contrast.ts | `` `${block.type}.${slot}: contrast ${ratio.toFixed(2)}:1 below ${threshold}:1 on ${bg}` `` | `validation.contrast.below_threshold` with `{blockType}`, `{slot}`, `{ratio}`, `{threshold}`, `{background}` |
| validation/invariants.ts | `` `Block "${reg.name}" in "${sec.type}" section (allowed: ${reg.allowedSections.join(', ')})` `` | `validation.integrity.wrong_section` with `{blockName}`, `{sectionType}`, `{allowed}` |

### Enum/map-based messages

| File | Map name | Keys | Notes |
|---|---|---|---|
| Inspector.tsx | `badge()` label map | `required_locked`, `required_editable`, `optional_default`, `optional_available` | User-visible compact labels are module-local constants; move to translation keys before render. |
| validation/block-data.ts | `VALID_DIRECTIONS`, `VALID_SERIES_ROLES` used in interpolated errors | dynamic `join(', ')` lists | Errors should use ICU placeholders for allowed values list. |

### Shared/duplicated messages

| Message | Appears in | Suggested consolidation |
|---|---|---|
| `Inspector` | Inspector.tsx, RightRail.tsx | Single `inspector.title` key |
| `Review`/review status terms | RightRail.tsx, ReviewPanel.tsx | Use workflow namespace (`review.*`, `workflow.*`) |
| `Add comment` | ReviewPanel title/button/tooltip | Single action key with context variants |
| `Resolve`/`Reopen`/`Edit`/`Delete` | ReviewPanel action controls | Shared generic action keys from glossary section 4 |
| `Export as PNG` and export-disabled explanations | TopBar.tsx + validation counts | Unified `export.*` namespace with plural handling |

## 4. Existing infrastructure compatibility

| Concern | Status | Notes |
|---|---|---|
| Client components can import `useTranslations` | yes | All audited TSX files have `'use client'`; no server-only blockers. |
| Server component usage needed | no | No audited file is a Server Component. |
| Module-level string constants | yes | `badge()` map in `Inspector.tsx`, `TAB_ORDER` labels/state in `RightRail.tsx`, and many validation module string templates are module-evaluated; convert by passing translated labels from component context or using key-based post-processing in UI layer. |

## 5. Shared components risk

| Component | Shared with public site | Risk | Notes |
|---|---|---|---|
| Inspector / RightRail / QAPanel / ReviewPanel / TopBar | no (admin-only) | low | Import graph shows editor root mounted via `app/admin/editor/[id]/AdminEditorClient.tsx` only. |
| validation/* modules | no direct public render | low | Messages flow into editor QA surfaces; not imported by public marketing/site routes. |

## 6. Summary

- Total files audited: 11
- Files with hardcoded strings: 10
- Total hardcoded strings found: 134
- Glossary coverage: covered 17 / partial 92 / new 25
- Validation pattern complexity: **complex**
- Module-level constant traps: 3 flagged
- Blockers for implementation: none

## 7. New terms requiring translation decisions

List includes every item marked **new** or phrase-level **partial** where exact canonical RU is unresolved.

| Key | EN | Suggested RU (TBD for founder review) |
|---|---|---|
| inspector.badge.optional_default | OPT·ON | TBD |
| inspector.badge.optional_available | OPT | TBD |
| inspector.template_mode.short | TPL | TBD |
| right_rail.aria_label | Right rail | TBD |
| validation.xlabels.array_required | xLabels must be an array | TBD |
| validation.xlabels.non_empty | xLabels cannot be empty | TBD |
| validation.xlabels.all_non_empty | all xLabels must be non-empty strings | TBD |
| validation.series.points_mismatch | series[i] "label": X points but Y xLabels | TBD |
| validation.row.vals_count_mismatch | row[i]: X vals but Y data columns | TBD |
| validation.density.ranked_bars_dense | Ranked Bars: N items — may be dense | TBD |
| validation.density.ranked_bars_height | Ranked Bars: too many items for this canvas height | TBD |
| validation.density.kpi_compare_cramped | KPI Compare: more than 4 items may be cramped | TBD |
| validation.density.visual_table_overflow | Visual Table: N rows — may overflow on size | TBD |
| validation.density.small_multiples_dense | Small Multiples: more than 9 cells may be too dense | TBD |
| qa.title | QA | TBD |
| qa.mode.aria | QA mode | TBD |
| export.disabled.loading_fonts | Export disabled: loading fonts… | TBD |
| qa.summary.compact | `${errs}err ${warns}warn` | TBD |
| debug.overlay.enable | Enable debug overlay | TBD |
| debug.overlay.disable | Disable debug overlay | TBD |
| debug.overlay.on | Debug overlay ON (Ctrl+Shift+D) | TBD |
| debug.overlay.off | Debug overlay OFF (Ctrl+Shift+D) | TBD |
| review.threads.title_count | Threads (N) | TBD |
| review.reply.to_thread | Reply to thread | TBD |
| review.history.show_all | Show all N | TBD |

## 8. Recommended implementation order

1. **`frontend-public/src/components/editor/components/RightRail.tsx` + `Inspector.tsx`** — high-visibility UI labels, limited branching, fast win.
2. **`frontend-public/src/components/editor/components/ReviewPanel.tsx`** — heavy user-facing copy and modal labels; establish `review.*` key namespace early.
3. **`frontend-public/src/components/editor/components/QAPanel.tsx` + `TopBar.tsx`** — these consume validation state and need pluralization/ARIA handling.
4. **`frontend-public/src/components/editor/validation/contrast.ts` and `validation/validate.ts`** — central message emitters; migrate interpolated patterns to ICU placeholders.
5. **`frontend-public/src/components/editor/validation/block-data.ts` + `validation/invariants.ts`** — standardize low-level validator messages and ensure consistent key strategy for index-based errors.

