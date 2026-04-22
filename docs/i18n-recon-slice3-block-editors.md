# i18n Recon — Slice 3: Block Editors

Date: 2026-04-22
Scope: block editor forms, block registry, block creation menu
Status: RECON COMPLETE
Previous slices: 1 merged, 2a merged, 2b in flight

## 1. Files audited

| File | Found | Block type handled | Hardcoded strings | Notes |
|---|---|---|---|---|
| `frontend-public/src/components/editor/components/block-editors/**/*` | No | — | — | Path not found in repo. |
| `frontend-public/src/components/editor/components/BlockEditor*.tsx` | No | — | — | No matching files. |
| `frontend-public/src/components/editor/components/BlockCreate*.tsx` | No | — | — | No matching files. |
| `frontend-public/src/components/editor/components/BlockMenu*.tsx` | No | — | — | No matching files. |
| `frontend-public/src/components/editor/components/BlockList*.tsx` | No | — | — | No matching files. |
| `frontend-public/src/components/editor/components/blocks/**/*` | No | — | — | Directory not found. |
| `frontend-public/src/components/editor/registry/blocks.ts` | Yes | All (registry) | Yes | Primary source for block `name` labels and inspector control labels (`ctrl[].l`). |
| `frontend-public/src/components/editor/registry/templates.ts` | Yes | Template picker (left panel) | Yes | Not a block editor form, but in requested scope and user-visible in template selection UI. |
| `frontend-public/src/components/editor/registry/guards.ts` | Yes | N/A | No (slice-relevant UI strings) | Contains validation/import errors; excluded from this slice’s implementation scope (2b in flight). |
| `frontend-public/src/components/editor/components/Inspector.tsx` *(discovered, in-scope by behavior)* | Yes | Generic inspector host | Mixed | Uses `useTranslations`; still renders hardcoded `c.l`/`c.opts` coming from BREG and data-editor children. |
| `frontend-public/src/components/editor/components/LeftPanel.tsx` *(discovered, in-scope by behavior)* | Yes | Block/template menu surfaces | Yes | Hosts tabs and block list; no explicit “BlockCreate/BlockMenu” file exists in this codebase. |
| `frontend-public/src/components/editor/components/data-editors/BarItemsEditor.tsx` *(discovered)* | Yes | `bar_horizontal` | Yes | Bespoke structured editor. |
| `frontend-public/src/components/editor/components/data-editors/KPIItemsEditor.tsx` *(discovered)* | Yes | `comparison_kpi` | Yes | Bespoke structured editor. |
| `frontend-public/src/components/editor/components/data-editors/LineSeriesEditor.tsx` *(discovered)* | Yes | `line_editorial` | Yes | Bespoke structured editor. |

## 2. Block registry (BREG) inventory

| Block type ID | `name` (EN) | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|
| `eyebrow_tag` | Eyebrow | `block.type.eyebrow_tag.name` | partial | надзаголовок (glossary has “eyebrow tag”; label here is shortened) |
| `headline_editorial` | Headline | `block.type.headline_editorial.name` | covered | заголовок |
| `subtitle_descriptor` | Subtitle | `block.type.subtitle_descriptor.name` | covered | подзаголовок |
| `hero_stat` | Hero Number | `block.type.hero_stat.name` | partial | ключевой показатель / число hero-блока (decision needed) |
| `delta_badge` | Delta Badge | `block.type.delta_badge.name` | covered | маркер изменения |
| `body_annotation` | Annotation | `block.type.body_annotation.name` | partial | аннотация / примечание (decision needed) |
| `source_footer` | Source | `block.type.source_footer.name` | partial | источник / подпись источника (decision needed) |
| `brand_stamp` | Brand | `block.type.brand_stamp.name` | partial | фирменная метка / бренд (decision needed) |
| `bar_horizontal` | Ranked Bars | `block.type.bar_horizontal.name` | partial | ранжированные столбцы / столбчатая диаграмма (decision needed) |
| `line_editorial` | Line Chart | `block.type.line_editorial.name` | covered | линейный график |
| `comparison_kpi` | KPI Compare | `block.type.comparison_kpi.name` | partial | KPI-сравнение (decision needed) |
| `table_enriched` | Visual Table | `block.type.table_enriched.name` | partial | визуальная таблица (decision needed) |
| `small_multiple` | Small Multiples | `block.type.small_multiple.name` | new | TBD |

## 3. Per-block-editor strings

### `frontend-public/src/components/editor/registry/blocks.ts`

Block type: `eyebrow_tag`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Tag | `ctrl[].l` | Field label | `block.field.tag.label` | partial | метка / надзаголовок |

Block type: `headline_editorial`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Headline | `ctrl[].l` | Field label | `block.field.headline.label` | covered | заголовок |
| 2 | Align | `ctrl[].l` | Field label | `block.field.align.label` | partial | выравнивание |
| 3 | left / center / right | `ctrl[].opts` | Segmented option labels | `block.option.align.left|center|right` | partial | по левому краю / по центру / по правому краю |

Block type: `subtitle_descriptor`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Subtitle | `ctrl[].l` | Field label | `block.field.subtitle.label` | covered | подзаголовок |

Block type: `hero_stat`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Value | `ctrl[].l` | Field label | `block.field.value.label` | covered | значение |
| 2 | Label | `ctrl[].l` | Field label | `block.field.label.label` | covered | метка |

Block type: `delta_badge`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Delta | `ctrl[].l` | Field label | `block.field.delta.label` | partial | изменение / дельта |
| 2 | Dir | `ctrl[].l` | Field label abbreviation | `block.field.direction.short_label` | new | TBD |
| 3 | positive / negative / neutral | `ctrl[].opts` | Segmented option labels | `block.option.direction.positive|negative|neutral` | partial | положительный / отрицательный / нейтральный |

Block type: `body_annotation`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Note | `ctrl[].l` | Field label | `block.field.note.label` | partial | примечание |

Block type: `source_footer`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Source | `ctrl[].l` | Field label | `block.field.source.label` | covered | источник |
| 2 | Method | `ctrl[].l` | Field label abbreviation | `block.field.method.short_label` | new | TBD |

Block type: `brand_stamp`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Position | `ctrl[].l` | Field label | `block.field.position.label` | partial | позиция |
| 2 | bottom-left / bottom-right | `ctrl[].opts` | Segmented option labels | `block.option.position.bottom_left|bottom_right` | partial | слева снизу / справа снизу |

Block type: `bar_horizontal`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Unit suffix | `ctrl[].l` | Field label | `block.field.unit_suffix.label` | partial | суффикс единицы |
| 2 | Benchmark line | `ctrl[].l` | Toggle label | `block.field.benchmark_line.label` | partial | линия ориентира |
| 3 | Bench value | `ctrl[].l` | Field label abbreviation | `block.field.benchmark_value.short_label` | new | TBD |
| 4 | Bench label | `ctrl[].l` | Field label abbreviation | `block.field.benchmark_label.short_label` | new | TBD |

Block type: `line_editorial`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Y unit | `ctrl[].l` | Field label | `block.field.y_unit.label` | partial | единица по оси Y |
| 2 | Area fill | `ctrl[].l` | Toggle label | `block.field.area_fill.label` | partial | заливка области |

Block type: `comparison_kpi`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | *(no `ctrl` labels in BREG)* | — | Uses bespoke `KPIItemsEditor` | — | — | — |

Block type: `table_enriched`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | *(no `ctrl` labels in BREG)* | — | No dedicated data-editor found in this slice scope | — | — | — |

Block type: `small_multiple`

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Y unit | `ctrl[].l` | Field label | `block.field.y_unit.label` | partial | единица по оси Y |

### `frontend-public/src/components/editor/components/data-editors/BarItemsEditor.tsx`

Block type: `bar_horizontal`

Pattern: bespoke structured list editor.

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | DATA ITEMS ({items.length}) | section header | Data list title | `block.data_items.title_count` | partial | элементы данных ({count}) |
| 2 | Flag | input `title` | Cell hint | `block.field.flag.title` | partial | флаг |
| 3 | Label | input `title` | Cell hint | `block.field.label.title` | covered | метка |
| 4 | Value | input `title` | Cell hint | `block.field.value.title` | covered | значение |
| 5 | Highlight | button `title` | Toggle hint | `block.field.highlight.title` | partial | выделить |
| 6 | Remove | button `title` | Delete item action | `block.item.remove.title` | covered | удалить |
| 7 | + ADD ITEM | button text | Add row action | `block.item.add.action` | partial | + добавить элемент |
| 8 | New | `add()` default item label | New row seed text (user-visible in input) | `block.item.new.default_label` | partial | новый |

### `frontend-public/src/components/editor/components/data-editors/KPIItemsEditor.tsx`

Block type: `comparison_kpi`

Pattern: bespoke card-list editor.

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | KPI CARDS ({items.length}) | section header | Card list title | `block.kpi_cards.title_count` | partial | KPI-карточки ({count}) |
| 2 | Remove KPI | button `title` | Delete card action | `block.kpi.remove.title` | partial | удалить KPI |
| 3 | Label | input placeholder | Field placeholder | `block.field.label.placeholder` | covered | метка |
| 4 | Value | input placeholder | Field placeholder | `block.field.value.placeholder` | covered | значение |
| 5 | Delta | input placeholder | Field placeholder | `block.field.delta.placeholder` | partial | изменение |
| 6 | + ADD KPI | button text | Add KPI action | `block.kpi.add.action` | partial | + добавить KPI |
| 7 | New Metric | `add()` default label | New card seed text | `block.kpi.new_metric.default_label` | partial | новая метрика |

### `frontend-public/src/components/editor/components/data-editors/LineSeriesEditor.tsx`

Block type: `line_editorial`

Pattern: bespoke series + axis editor.

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | X LABELS | section header | Axis label section title | `block.x_labels.title` | partial | подписи оси X |
| 2 | Comma-separated labels | input `title` | Input hint | `block.x_labels.comma_hint.title` | partial | подписи через запятую |
| 3 | SERIES ({series.length}) | section header | Series list title | `block.series.title_count` | partial | ряды ({count}) |
| 4 | Remove series | button `title` | Delete series action | `block.series.remove.title` | partial | удалить ряд |
| 5 | Series name | input placeholder | Field placeholder | `block.series.name.placeholder` | partial | название ряда |
| 6 | Primary | `<option>` text | Role option | `block.series.role.primary` | partial | основной |
| 7 | Benchmark | `<option>` text | Role option | `block.series.role.benchmark` | partial | ориентир |
| 8 | Secondary | `<option>` text | Role option | `block.series.role.secondary` | partial | вторичный |
| 9 | Comma-separated values | input `title` | Input hint | `block.series.values.comma_hint.title` | partial | значения через запятую |
| 10 | + ADD SERIES | button text | Add series action | `block.series.add.action` | partial | + добавить ряд |
| 11 | New Series | `addSeries()` default label | New series seed text | `block.series.new.default_label` | partial | новый ряд |

## 4. Block creation menu strings

No dedicated `BlockCreate*`, `BlockMenu*`, or `BlockList*` file exists in current tree.
The nearest menu surfaces are in `LeftPanel.tsx`:
- block list tab (`blocks`) renders existing block names (`BREG[block.type].name`);
- template selection tab (`templates`) renders template families/variants/descriptions.

| # | String (EN) | Location | Context | Suggested key | Glossary coverage | Canonical RU |
|---|---|---|---|---|---|---|
| 1 | Left panel sections | `aria-label` on tablist | Left panel tabs ARIA | `left_panel.sections.aria` | partial | разделы левой панели |
| 2 | Tpl / Blk / Thm | tab text | Tab short labels | `left_panel.tab.templates.short` etc. | new | TBD |
| 3 | `{k} tab` | tab `aria-label` | Tab ARIA labels | `left_panel.tab.aria` | partial | вкладка {name} |
| 4 | Select block: {r.name} | block row `aria-label` | Block selection ARIA | `block.select.aria` | partial | выбрать блок: {name} |
| 5 | unresolved comment(s) | unresolved pill `title` | Comment-count tooltip | `review.unresolved_comments.title_count` | partial | нерешённые комментарии |
| 6 | Hide {r.name} / Show {r.name} | visibility button `aria-label` | Block visibility ARIA | `block.visibility.hide_show.aria` | partial | скрыть/показать {name} |
| 7 | Hide block / Show block | visibility button `title` | Block visibility tooltip | `block.visibility.hide_show.title` | partial | скрыть/показать блок |
| 8 | Palette / Background / Size | section headers | Theme settings labels | `theme.palette.title` etc. | covered/partial | палитра / фон / размер |
| 9 | Palette: {v.n} / Background: {v.n} / Size: {v.n} {w}x{h} | item `aria-label`s | Option ARIA labels | `theme.option.*.aria` | partial | палитра/фон/размер: ... |
| 10 | `v{schema} · {sections}sec · {blocks}blk` | footer status line | Compact metadata abbreviations | `left_panel.footer.summary` | new | TBD |

### Additional menu-adjacent inventory from `registry/templates.ts`

Template picker in `LeftPanel` uses these registry literals directly:
- `fam` labels (e.g., “Single Stat Hero”, “Insight Card”, “Ranked Bars”, “Line Editorial”, “Comparison”, “Visual Table”, “Small Multiples”)
- `vr` variant names (e.g., “Number + Delta”, “Simple Ranking”, “2×3 Grid”)
- `desc` text (e.g., “Giant number with change”, “Time series with area fill”)

All are user-visible and currently hardcoded module-level constants.

## 5. Shared field labels (candidates for consolidation)

| Term | Appears in editors | Suggested shared key |
|---|---|---|
| Label | `hero_stat`, `BarItemsEditor`, `KPIItemsEditor` | `block.field.label.label` + `block.field.label.placeholder/title` |
| Value | `hero_stat`, `BarItemsEditor`, `KPIItemsEditor` | `block.field.value.label` + `block.field.value.placeholder/title` |
| Delta | `delta_badge`, `KPIItemsEditor` | `block.field.delta.label` + `block.field.delta.placeholder` |
| Source | `source_footer`, left-panel list context | `block.field.source.label` |
| Headline | `headline_editorial` | `block.field.headline.label` |
| Subtitle | `subtitle_descriptor` | `block.field.subtitle.label` |
| Align + Left/Center/Right | `headline_editorial` | `block.field.align.label` + `block.option.align.*` |
| Y unit | `line_editorial`, `small_multiple` | `block.field.y_unit.label` |
| Remove | all three data-editors | `common.remove.verb` / contextual variants |
| Add item / Add KPI / Add series | all three data-editors | `common.add.verb` + entity keys |

## 6. Module-level / static-schema traps

| File | Pattern | Mitigation |
|---|---|---|
| `registry/blocks.ts` | Module-level `BREG` object has user-visible `name` and `ctrl[].l/opts` string literals. | Store stable translation keys in registry (e.g., `nameKey`, `labelKey`, `optionKey`) and translate in component render path. |
| `registry/templates.ts` | Module-level `TPLS` has user-visible `fam`, `vr`, `desc` literals. | Same approach: template metadata should carry keys, not direct English strings. |
| `components/LeftPanel.tsx` | Module-level `TEMPLATE_FAMILIES` grouping keyed by `t.fam` (literal EN); tab short labels are inline constants. | Group by translated display key at render time or by stable family ID separate from localized label. |
| `components/data-editors/*.tsx` | UI copy embedded in function bodies (`title`, headers, placeholders, add/remove labels). | Add translator hook + key mapping in each editor; keep structure logic unchanged. |

## 7. Summary

- Total files audited: 14
- Files with hardcoded strings: 6
- Total hardcoded strings found (slice-relevant): 68
- BREG entries: 13
- Glossary coverage: covered 11 / partial 50 / new 7
- Shared-term candidates: 10
- Module-level traps: 4
- Blockers: none

## 8. New terms requiring translation decisions

| Key | EN | Suggested RU (TBD) |
|---|---|---|
| `block.type.small_multiple.name` | Small Multiples | TBD |
| `left_panel.tab.templates.short` | Tpl | TBD |
| `left_panel.tab.blocks.short` | Blk | TBD |
| `left_panel.tab.theme.short` | Thm | TBD |
| `block.field.direction.short_label` | Dir | TBD |
| `block.field.method.short_label` | Method | TBD |
| `left_panel.footer.summary` | `v{schema} · {sections}sec · {blocks}blk` | TBD |

## 9. Recommended implementation order

1. **Shared field labels namespace first** (`block.field.*`, `block.option.*`, plus common add/remove verbs). This reduces duplication across BREG control labels and bespoke data-editors.
2. **BREG names second** (`block.type.*.name`) because these labels feed left-panel block list and validation `{blockName}` params.
3. **LeftPanel creation/menu-adjacent strings third** (tabs, ARIA, visibility titles, unresolved count).
4. **Data-editor components fourth** (`BarItemsEditor`, `KPIItemsEditor`, `LineSeriesEditor`) to remove remaining hardcoded placeholders/titles/button text.
5. **Template registry literals last** (`TPLS.fam/vr/desc`) since this is user-facing but orthogonal to per-block inspector editing.
