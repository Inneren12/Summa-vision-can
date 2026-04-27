# Summa Vision — Infographic Editor Architecture

**Версия:** 1.1
**Статус:** Итоговое решение по архитектуре блочного редактора
**Основа:** Анализ 12 лейаут-архетипов Visual Capitalist (~100 статей), Design System v3.2, рекомендации по UX-модели, production-рекомендации по контентным ограничениям и QA
**Инструменты:** React Editor — production tool; Claude Artifacts — design lab & prototyping (вместо Figma)

---

## 1. Продуктовая философия

### 1.1 Позиционирование

Summa Vision — forensic public finance platform с editorial качеством визуализаций. Не Bloomberg-терминал. Не новостной outlet. Не копия Visual Capitalist.

### 1.2 Ключевые отличия от VC

| Аспект | Visual Capitalist | Summa Vision |
|--------|-------------------|-------------|
| Формат | Статичная PNG-инфографика | Интерактивный embed + статичный export |
| Монетизация | Реклама в контенте, попапы | Lead funnel (email → hi-res download) |
| Цвет | Хаос по категориям | Единая палитра, цвет = данные |
| Типографика | Тяжёлый Black + антиква | Единый гротеск (Bricolage + DM Sans) |
| Фон | Тёмный (#0a0e1a) | Dark mode primary, light mode для export |
| Макет | 3 колонки (реклама) | 2 колонки (данные + KPI) |
| Контекст | Инфографика без подписей | Source + methodology обязательны |

### 1.3 Принцип "Данные — единственный источник света"

Бренд и UI не перетягивают визуальный приоритет у графика. Каждый пиксель — для данных. Минимум декора, максимум data-ink ratio.

---

## 2. Лейаут-архетипы (из анализа VC)

### 2.1 Полная таксономия (12 архетипов)

| # | Архетип | Частота | Нарратив |
|---|---------|---------|----------|
| 1 | Ранжированный бар | ~24% | X намного больше Y |
| 1a | Парные / сгруппированные бары | ~4% | Кто выиграл, кто проиграл |
| 1b | Гантель-чарт | ~1% | Разрыв вырос / сократился |
| 2 | Картографический | ~29% | Где это происходит |
| 3 | Пропорциональные области | ~6% | Масштабное неравенство |
| 4 | Герой-статистика + чарт | ~8% | Один оглушительный факт |
| 5 | Временной ряд | ~5% | Как изменился мир |
| 6 | Малые кратные | ~4% | Паттерн + исключения |
| 7 | Визуальная таблица | ~5% | Полный профиль данных |
| 8 | Флоу / Санки | ~3% | Откуда это берётся |
| 9 | Радиальный бар | ~1% | Круговая динамика |
| 10 | Демографическая пирамида | ~2% | Общество меняет форму |
| 11 | Иллюстративный инфографик | ~3% | N фактов, меняющих взгляд |
| 12 | Комбинированный (карта + чарт) | ~4% | Где + в каком порядке |

### 2.2 Реализация по тирам

**Tier 1 — v1 (покрывает ~50% контента VC):**

- #1 Ranked Bar (24%)
- #1a Dual/Grouped Bar (4%)
- #4 Hero Stat + Chart (8%)
- #5 Time Series (5%)
- #6 Small Multiples (4%)
- #7 Visual Table (5%)

**Tier 2 — v2 (ещё ~16%):**

- #8 Sankey/Flow (3%) — требует D3
- #3 Treemap/Circle Pack (6%) — layout algorithms
- #11 Illustrated Infographic (3%) — кастомные иконки
- #12 Combo Map+Chart (4%) — зависит от geo

**Tier 3 — бэклог:**

- #2 Maps (29%) — TopoJSON, проекции, geo-рендеринг
- #9 Radial Bar (1%)
- #10 Population Pyramid (2%)
- #1b Dumbbell (1%)

### 2.3 Мета-паттерны VC (забираем в систему)

1. **Тезисный заголовок** — не "GDP by Country", а "China Now Dominates Manufacturing"
2. **Брендированные серии** — "RANKED:", "CHARTED:", "MAPPED:" как eyebrow
3. **Флаги/логотипы как обязательный якорь** — в каждом ranked item
4. **Одна акцентная сущность** — ТОП-1 выделен, остальные — контекст
5. **Тёмный фон** — фирменный стиль, яркие акценты работают лучше
6. **Source + methodology в подвале** — обязателен в каждом шаблоне

### 2.4 Что VC намеренно избегает (и мы тоже)

Scatter plots, network graphs, waterfall charts, candlestick, box plots, gauges — всё что требует от читателя более одного когнитивного шага. Инфографика должна быть понятна за 3-5 секунд.

---

## 3. Блочная архитектура

### 3.1 Иерархия сущностей

```
Project
  └── Theme (colors, typography, spacing)
  └── Page / Artboard
        └── size, background
        └── Sections (header, hero, chart_area, footer)
              └── Blocks (headline, hero_stat, bar_chart...)
                    └── Elements (text, shape, icon, data binding)
```

### 3.2 Принципы

- **Template = composed blocks.** Шаблон — стартовая сборка блоков, не монолитная сущность.
- **Block = переиспользуемый модуль** с default props, renderer, inspector config, validation rules.
- **Registry подход.** Новый блок = один файл. `blockRegistry["headline_editorial"]`.
- **Config-driven.** Каждый шаблон описывается JSON, renderer читает schema.

### 3.3 Полный каталог блоков (26 блоков, 5 категорий)

#### TEXT BLOCKS (6)

| Block ID | Название | Описание |
|----------|----------|----------|
| `headline_editorial` | Editorial Headline | Крупный тезисный заголовок (40-72px). Вывод, не описание |
| `eyebrow_tag` | Series Tag / Eyebrow | Метка серии: "RANKED:", "STATISTICS CANADA · TABLE 18-10-0004" |
| `body_annotation` | Inline Annotation | 1-3 строки пояснения прямо на чарте. Callout с стрелкой |
| `source_footer` | Source + Methodology | Источник + дата + метод. Обязателен в каждом шаблоне |
| `subtitle_descriptor` | Subtitle / Descriptor | Вторая строка под headline: единица, период, контекст |
| `callout_box` | Callout / Insight Box | Выделенный блок с ключевым выводом, рамка или фон |

#### DATA BLOCKS (6)

| Block ID | Название | Описание |
|----------|----------|----------|
| `hero_stat` | Hero Number | Одно гигантское число (80-120px) + unit + delta. "$39T", "6.73%" |
| `delta_badge` | Delta / Change Badge | Стрелка + изменение. Цвет: positive/negative. "+247 bps", "▲ 12.3%" |
| `kpi_row` | KPI Card Row | 3-4 горизонтальных stat-карточки: число + подпись + delta |
| `ranked_item` | Ranked List Item | Строка рейтинга: rank # + icon/flag + label + bar + value |
| `comparison_pair` | Comparison Pair | Два значения рядом: "было/стало", "рост/падение" |
| `legend_block` | Legend / Color Key | Цветовые маркеры + подписи для multi-series чартов |

#### CHART BLOCKS (6)

| Block ID | Название | Описание |
|----------|----------|----------|
| `bar_horizontal` | Horizontal Bar Chart | Горизонтальные бары, labels слева, values справа. Highlight top-N |
| `bar_grouped` | Grouped / Dual Bar | Два бара на строку или дивергентный формат |
| `line_editorial` | Line / Area Chart | Временной ряд. 1-3 линии, area fill, event annotations |
| `small_multiple_cell` | Small Multiple Cell | Мини-чарт в сетке: spark + label + число. Единая шкала |
| `table_enriched` | Enriched Table | Таблица с heatmap, inline бары, флаги, badges |
| `sparkline_inline` | Inline Sparkline | Миниатюрный line chart без осей, для table cell или KPI |

#### STRUCTURAL BLOCKS (5)

| Block ID | Название | Описание |
|----------|----------|----------|
| `brand_stamp` | Brand / Logo Stamp | Лого Summa Vision, позиция bottom-right. Обязателен для export |
| `divider_line` | Section Divider | Линия 1px между секциями. Опционально с текстовой меткой |
| `background_layer` | Background Layer | Фон: solid / gradient / pattern / texture. Layer 0 |
| `safe_zone` | Safe Zone Overlay | Невидимый padding для social export. Только guide, не рендерится |
| `card_container` | Card Container | Обёртка с border, radius, shadow, padding |

#### ICON / MEDIA BLOCKS (3)

| Block ID | Название | Описание |
|----------|----------|----------|
| `flag_icon` | Country Flag | SVG флаг. Обязателен в ranked items (мета-паттерн #3 VC) |
| `category_icon` | Category / Topic Icon | Иконка темы: housing, energy, demographics |
| `accent_shape` | Decorative Accent | Геометрия для визуального обогащения. Не несёт данных |

---

## 4. Шаблоны v1 (6 шаблонов из 26 блоков)

### 4.1 Single Stat Hero

**Архетип:** #4 (Hero Stat + Chart)
**Нарратив:** "Один оглушительный факт"

```
Sections:
  header:
    - eyebrow_tag
    - headline_editorial
    - subtitle_descriptor
  hero:
    - hero_stat
    - delta_badge
  context:              (optional)
    - body_annotation
    - kpi_row
  footer:
    - source_footer
    - brand_stamp
Layer 0: background_layer
```

**Пример:** "Canadian Mortgage Rates Hit 15-Year High" → 6.73% → +247 bps since Jan 2022

### 4.2 Ranked Bar

**Архетип:** #1 (Ranked Bar) — самый частый формат VC (24%)
**Нарратив:** "X намного больше Y"

```
Sections:
  header:
    - eyebrow_tag ("RANKED:")
    - headline_editorial
    - subtitle_descriptor
  chart:
    - ranked_item × N (10-30 позиций)
      каждый содержит: flag_icon + label + bar_horizontal + value
    - [highlight: true для ТОП-1]
  context:              (optional)
    - callout_box
    - legend_block
  footer:
    - source_footer
    - brand_stamp
Layer 0: background_layer
```

**Пример:** "Where OECD Workers Are Most Productive" → Ireland $151/hr → ... → Colombia $21/hr

### 4.3 Dual Ranking

**Архетип:** #1a (Grouped/Dual Bar)
**Нарратив:** "Кто выиграл, кто проиграл"

```
Sections:
  header:
    - eyebrow_tag
    - headline_editorial
  left_column:
    - subtitle_descriptor ("TOP GROWTH")
    - ranked_item × N (positive, green)
  right_column:
    - subtitle_descriptor ("TOP DECLINE")
    - ranked_item × N (negative, red)
  footer:
    - source_footer
    - brand_stamp
Layer 0: background_layer
```

**Пример:** "Population Growth vs Decline 2000-2025" → Qatar +423% | Ukraine −33%

### 4.4 Line Editorial

**Архетип:** #5 (Time Series)
**Нарратив:** "Вот как изменился мир за N лет"

```
Sections:
  header:
    - eyebrow_tag ("CHARTED:")
    - headline_editorial
    - subtitle_descriptor
  chart:
    - line_editorial (1-3 series, area fill, annotations)
    - legend_block
  annotations:          (optional)
    - body_annotation × 1-3 (привязаны к точкам на чарте)
  context:              (optional)
    - kpi_row
  footer:
    - source_footer
    - brand_stamp
Layer 0: background_layer
```

**Пример:** "Canada's Inflation Journey: From Pandemic to New Normal" → CPI line 2019-2026 + BoC target

### 4.5 Small Multiples

**Архетип:** #6 (Small Multiples)
**Нарратив:** "Паттерн везде одинаковый — но вот исключения"

```
Sections:
  header:
    - eyebrow_tag
    - headline_editorial
    - subtitle_descriptor
  grid:
    - small_multiple_cell × N (2×3, 3×4, или 2×5 сетка)
      каждый содержит: label + flag_icon + mini chart + key number
    - [единая шкала для всех ячеек]
  footer:
    - source_footer
    - brand_stamp
Layer 0: background_layer
```

**Пример:** "A Rocky Month for Global Stocks" → 6 sparklines: NY, London, Frankfurt, Shanghai, HK, Tokyo

### 4.6 Visual Table

**Архетип:** #7 (Visual Table)
**Нарратив:** "Полный профиль: все метрики сразу"

```
Sections:
  header:
    - eyebrow_tag
    - headline_editorial
    - subtitle_descriptor
  table:
    - table_enriched
      строки: сущности (флаги + labels)
      столбцы: 3-8 атрибутов
      ячейки: conditional formatting (heatmap, inline bars, badges)
  context:              (optional)
    - callout_box
    - legend_block
  footer:
    - source_footer
    - brand_stamp
Layer 0: background_layer
```

**Пример:** "Best and Worst Countries for Taxes 2024" → 38 стран × 7 налоговых рангов

---

## 5. JSON Schema — Document Model

### 5.1 Структура проекта

```json
{
  "project": {
    "id": "proj_001",
    "name": "Canadian Mortgage Rates Editorial",
    "version": 1,
    "mode": "simple",
    "themeId": "summa_dark",
    "pages": [
      {
        "id": "page_001",
        "name": "Hero Card",
        "size": "instagram_1080",
        "background": {
          "type": "gradient",
          "preset": "gradient_warm",
          "customColors": null
        },
        "sections": [
          {
            "id": "sec_header",
            "type": "header",
            "blocks": [
              {
                "id": "blk_001",
                "type": "eyebrow_tag",
                "props": {
                  "text": "STATISTICS CANADA · TABLE 18-10-0004",
                  "series": null
                }
              },
              {
                "id": "blk_002",
                "type": "headline_editorial",
                "props": {
                  "text": "Canadian Mortgage Rates Hit 15-Year High",
                  "maxLines": 3,
                  "align": "left"
                }
              }
            ]
          },
          {
            "id": "sec_hero",
            "type": "hero",
            "blocks": [
              {
                "id": "blk_003",
                "type": "hero_stat",
                "props": {
                  "value": "6.73%",
                  "label": "Average 5-year fixed rate, March 2026",
                  "valueBinding": null
                }
              },
              {
                "id": "blk_004",
                "type": "delta_badge",
                "props": {
                  "value": "+247 bps",
                  "direction": "negative",
                  "since": "Jan 2022"
                }
              }
            ]
          },
          {
            "id": "sec_footer",
            "type": "footer",
            "blocks": [
              {
                "id": "blk_005",
                "type": "source_footer",
                "props": {
                  "text": "Source: Statistics Canada, Table 18-10-0004-01",
                  "methodology": "Rates represent posted rates from chartered banks"
                }
              },
              {
                "id": "blk_006",
                "type": "brand_stamp",
                "props": {
                  "position": "bottom-right"
                }
              }
            ]
          }
        ]
      }
    ],
    "dataSources": [],
    "exportPresets": ["png_instagram", "png_twitter", "png_reddit"]
  }
}
```

### 5.2 Theme schema

```json
{
  "theme": {
    "id": "summa_dark",
    "name": "Summa Dark",
    "mode": "dark",
    "colors": {
      "bg": "#0B0D11",
      "surface": "#15181E",
      "textPrimary": "#F3F4F6",
      "textSecondary": "#8B949E",
      "textMuted": "#5C6370",
      "accent": "#FBBF24",
      "primary": "#22D3EE",
      "positive": "#0D9488",
      "negative": "#E11D48"
    },
    "dataPalette": ["#3B82F6", "#A78BFA", "#2DD4BF", "#F97316", "#94A3B8", "#22D3EE", "#E11D48"],
    "typography": {
      "display": "Bricolage Grotesque",
      "body": "DM Sans",
      "data": "JetBrains Mono"
    },
    "spacing": {
      "xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32, "2xl": 48, "3xl": 64
    },
    "radius": {
      "sm": 2, "md": 6, "lg": 8
    }
  }
}
```

### 5.3 Block definition schema (registry entry)

```json
{
  "type": "hero_stat",
  "category": "data",
  "displayName": "Hero Number",
  "description": "One giant number with unit and delta",
  "defaultProps": {
    "value": "0",
    "label": "Label",
    "valueBinding": null,
    "fontSize": 120,
    "align": "center"
  },
  "inspectorControls": [
    { "key": "value", "control": "text", "label": "Value" },
    { "key": "label", "control": "text", "label": "Label" },
    { "key": "fontSize", "control": "slider", "min": 48, "max": 200, "label": "Font Size" },
    { "key": "align", "control": "segmented", "options": ["left", "center", "right"], "label": "Align" },
    { "key": "valueBinding", "control": "dataBinding", "label": "Data Source" }
  ],
  "validationRules": [
    { "rule": "required", "field": "value", "message": "Hero stat must have a value" }
  ],
  "allowedParents": ["hero", "context"],
  "simpleModeVisible": true
}
```

---

## 6. Размеры и export presets

| Preset ID | Платформа | Размер | Aspect |
|-----------|-----------|--------|--------|
| `instagram_1080` | Instagram Feed | 1080×1080 | 1:1 |
| `instagram_portrait` | Instagram Feed | 1080×1350 | 4:5 |
| `instagram_story` | Instagram Story | 1080×1920 | 9:16 |
| `twitter_landscape` | Twitter/X | 1200×675 | 16:9 |
| `reddit_standard` | Reddit | 1200×900 | 4:3 |
| `linkedin_landscape` | LinkedIn | 1200×627 | ~1.9:1 |
| `long_infographic` | Long-form | 1200×auto | Variable |

Safe areas для каждого preset:
- Top: 48px
- Bottom: 80px (brand stamp zone)
- Left/Right: 48px
- Instagram Story: top 120px, bottom 100px (UI overlay zones)

---

## 7. UX-модель редактора

### 7.1 Три уровня свободы

**Template mode (default)** — для контент-редактора:

Пользователь может: менять текст в разрешённых полях, вставить числа/данные, выбрать size preset, экспортировать.

Пользователь НЕ может: двигать блоки, менять layout, тему, сетку, palette, удалять обязательные блоки.

**Editor mode** — для маркетинга / senior editor:

Дополнительно: двигать блоки в рамках сетки, менять варианты блоков, палитру, фон.

Не может: менять тему, brand tokens, safe zones, сетку, JSON.

**Design mode** — для founder / дизайнера:

Всё: custom blocks, grid настройки, token editing, JSON template editing, block registry, safe zone override.

### 7.2 Layout интерфейса

```
┌─────────────────────────────────────────────────────────────┐
│  TOP BAR                                                     │
│  [Logo] [Template name] [Template/Editor/Design ▾]          │
│  [Undo][Redo] [Size preset ▾] [Preview] [🟢 Ready] [Export]│
│  [Save] [Publish]                                           │
├────────────┬────────────────────────────────┬────────────────┤
│ LEFT PANEL │        CENTER CANVAS           │  RIGHT PANEL   │
│            │                                │                │
│ Tab 1:     │   ┌──────────────────────┐     │  INSPECTOR     │
│ Document   │   │                      │     │                │
│  - pages   │   │    INFOGRAPHIC       │     │  [Selected:    │
│  - sections│   │    PREVIEW           │     │   headline]    │
│  - layers  │   │                      │     │                │
│            │   │    (60%+ of screen)  │     │  Text: [____]  │
│ Tab 2:     │   │                      │     │  72/80 chars   │
│ Templates  │   │                      │     │  Size: [--●-]  │
│  - families│   └──────────────────────┘     │  Align: [L C R]│
│  - variants│                                │  Color: [●]    │
│  - search  │   [Zoom] [Fit] [Grid toggle]   │                │
│            │                                │  Theme:        │
│ Tab 3:     │ ┌────────────────────────────┐ │  [Dark ▾]      │
│ Blocks     │ │ QUALITY CHECK              │ │                │
│  - text    │ │ ✅ Source ✅ Brand          │ │  Palette:      │
│  - data    │ │ ⚠️ Headline 72/80         │ │  [Housing ▾]   │
│  - chart   │ │ ❌ Contrast 3.8:1         │ │                │
│  - struct  │ │ Status: 1 err, 1 warn     │ │  Background:   │
│            │ └────────────────────────────┘ │  [Gradient ▾]  │
│ Tab 4:     │                                │                │
│ Data       │                                │                │
├────────────┴────────────────────────────────┴────────────────┤
│  STATUS: Layer 0-Background · 1080×1080 · Autosaved 12:30   │
└─────────────────────────────────────────────────────────────┘
```

Canvas должен занимать 60%+ экрана. Inspector справа — свойства только выбранного блока.

---

## 8. Data flow

### 8.1 Три варианта ввода данных

**Вариант 1: Manual** — пользователь вписывает headline, числа, source руками.

**Вариант 2: CSV/JSON paste** — вставляет данные, система предлагает chart type, назначает X/Y, labels.

**Вариант 3: Saved dataset** — выбирает из сохранённых StatCan datasets (через CubeCatalog API).

### 8.2 Data binding в блоках

```json
{
  "value": "6.73%",
  "valueBinding": {
    "sourceId": "ds_statcan_18100004",
    "field": "current_rate",
    "format": "percent_2"
  }
}
```

Блок поддерживает: static props (введено руками) ИЛИ data-bound props (привязано к dataset). Binding перезаписывает static при наличии данных.

---

## 9. Технический стек

### 9.1 Frontend (Editor)

- **React** + TypeScript
- **Zustand** — editor state (document, UI, session)
- **React Query** — серверные запросы (save, publish, load datasets)
- **Canvas API** — рендеринг инфографики (как в текущем прототипе)
- **dnd-kit** — drag-and-drop блоков (v2)
- **zod** — валидация JSON schema
- **react-hook-form** — inspector forms

### 9.2 Размещение

Next.js страница `/admin/editor` с API Key защитой. Общий codebase с публичным сайтом. Flutter-админка остаётся для операционных задач (jobs, KPI, cube search).

### 9.3 State architecture (4 слоя)

| Слой | Содержимое | Хранилище |
|------|-----------|-----------|
| Document | pages, blocks, elements, theme, bindings | Zustand + persist to backend |
| UI | selectedNodeId, activeSidebarTab, zoom, mode | Zustand (ephemeral) |
| Session | undo/redo stack, dirty flags, clipboard, drag state | Zustand (ephemeral) |
| Derived | resolved styles, computed layout, validation warnings | Computed from Document |

### 9.4 Command system

Все мутации документа — через команды, не прямой setState:

```
addBlock(sectionId, blockType, position)
removeBlock(blockId)
updateProps(blockId, partialProps)
moveBlock(blockId, targetSectionId, position)
duplicateBlock(blockId)
changeTheme(themeId)
resizePage(sizePreset)
bindDataField(blockId, propKey, sourceField)
```

Это даёт: undo/redo, autosave, change log, future collaboration.

---

## 10. Validation

### 10.1 Обязательные проверки перед export

| Правило | Сообщение |
|---------|----------|
| headline пустой | "Add a headline to your infographic" |
| source_footer отсутствует | "Source attribution is required" |
| brand_stamp отсутствует | "Brand stamp is required for export" |
| chart без данных | "Chart block has no data" |
| текст выходит за safe zone | "Text overflows the safe area" |
| low contrast text/bg | "Text may not be readable on this background" |

### 10.2 Warnings (не блокируют export)

- Empty callout_box
- More than 30 ranked_items (рекомендуется 10-25)
- Headline longer than 60 characters
- Missing delta_badge on hero_stat

---

## 11. Backend интеграция

### 11.1 API endpoints (из PR #85)

```
POST   /api/v1/admin/publications           → создать DRAFT
GET    /api/v1/admin/publications            → список (filter по status)
GET    /api/v1/admin/publications/{id}       → получить одну
PATCH  /api/v1/admin/publications/{id}       → обновить поля
POST   /api/v1/admin/publications/{id}/publish   → DRAFT → PUBLISHED
POST   /api/v1/admin/publications/{id}/unpublish → PUBLISHED → DRAFT
```

### 11.2 Что хранится в Publication

| Поле | Тип | Описание |
|------|-----|----------|
| headline | str | Тезисный заголовок |
| chart_type | str | Тип шаблона (single_stat, ranked_bar, etc.) |
| eyebrow | str | Серия/источник |
| description | str | Короткое описание для gallery |
| source_text | str | Source attribution |
| footnote | str | Methodology note |
| visual_config | JSON (Text) | Полный JSON document model |
| s3_key_lowres | str | CDN path для gallery preview |
| s3_key_highres | str | Private path для hi-res download |
| status | enum | DRAFT / PUBLISHED |
| published_at | datetime | Когда опубликовано |

### 11.3 Flow: Editor → Backend → Gallery

1. Editor: пользователь создаёт инфографику через блоки
2. Save: `POST /admin/publications` с visual_config JSON + editorial полями
3. Render: Canvas API рендерит PNG → upload to S3 (lowres + highres)
4. Publish: `POST /admin/publications/{id}/publish`
5. Gallery: `GET /api/v1/public/graphics` → Next.js ISR показывает на сайте
6. Lead: пользователь хочет hi-res → email → magic link → download

---

## 12. Контентные ограничения (Copy-fit Rules)

### 12.1 Жёсткие лимиты по блокам

| Block | Ограничение | При нарушении |
|-------|-------------|---------------|
| `headline_editorial` | Max 80 символов, max 3 строки | Warning "Headline too long", red outline, предложение сократить |
| `eyebrow_tag` | Max 60 символов, 1 строка | Hard truncate с ellipsis |
| `subtitle_descriptor` | Max 120 символов, max 2 строки | Warning + auto-shrink font |
| `body_annotation` | Max 200 символов, max 4 строки | Hard truncate |
| `source_footer` | Max 200 символов | Warning |
| `hero_stat` value | Max 10 символов | Hard limit, reject input |
| `hero_stat` label | Max 60 символов, 1 строка | Truncate |
| `ranked_item` label | Max 30 символов | Truncate |
| `kpi_row` | Max 4 карточки | UI не позволяет добавить 5-ю |
| `callout_box` | Max 150 символов | Warning |
| Charts per page | Max 2 (1 primary + 1 sparkline) | Block limit enforced |
| Ranked items per template | Max 30 (рекомендация 10-25) | Warning at 25, hard limit at 30 |

### 12.2 Overflow safety

Editor должен:
- Показывать overflow визуально (красная рамка вокруг блока, выходящего за safe zone)
- Предупреждать при превышении лимита символов (real-time counter)
- Автоматически держать safe area (48px по краям)
- Предлагать сокращение через AI (v2 — Gemini) или manual trim
- Блокировать export при critical overflow (текст за пределами canvas)

### 12.3 Accessibility и readability checks

| Проверка | Порог | Уровень |
|----------|-------|---------|
| Contrast ratio (text on bg) | Min 4.5:1 (WCAG AA) | Error — блокирует export |
| Contrast ratio на градиенте | Проверять по самой светлой точке | Warning |
| Min font size (export) | 10px effective | Warning |
| Min font size (mobile view) | 12px effective | Warning |
| Плотность элементов | Max 70% fill ratio per section | Warning |
| Bar labels readable | Min 8px | Warning |

---

## 13. Lockable Structure & Access Levels

### 13.1 Три уровня свободы (не два)

| Уровень | Кто | Может | Не может |
|---------|-----|-------|----------|
| **Template mode** | Контент-редактор | Менять текст, числа, данные в разрешённых полях | Двигать блоки, менять layout, тему, сетку |
| **Editor mode** | Маркетинг / senior editor | + двигать блоки в рамках сетки, менять варианты блоков, палитру | Менять тему, brand tokens, safe zones, сетку |
| **Design mode** | Founder / дизайнер | Всё: custom blocks, grid, tokens, JSON editing | — |

### 13.2 Lockable zones (что нельзя сломать)

Следующие элементы заблокированы в Template mode и Editor mode:

- **Сетка (grid)** — расположение секций фиксировано
- **Safe margins** — 48px по краям, не перемещаемы
- **Brand zone** — brand_stamp position и visibility
- **Source footer** — обязателен, не может быть удалён
- **Обязательные labels** — eyebrow, headline, source минимум
- **Theme tokens** — цвета, шрифты, spacing
- **Export presets** — размеры и safe areas
- **CTA / footer structure** — footer section locked

### 13.3 Block-level locks

В JSON schema каждого блока:

```json
{
  "type": "source_footer",
  "locked": true,
  "lockLevel": "template",
  "removable": false,
  "editableProps": ["text", "methodology"],
  "lockedProps": ["position", "fontSize", "color"]
}
```

`locked: true` + `lockLevel: "template"` = только Design mode может изменить или удалить.

---

## 14. Document Workflow & States

### 14.1 Статусы документа

```
DRAFT → IN_REVIEW → APPROVED → EXPORTED → PUBLISHED
  ↑         |          |
  └─────────┘          |
  (revisions)          |
                       ↓
                   PUBLISHED → UNPUBLISHED (archive)
```

| Статус | Кто устанавливает | Что разрешено |
|--------|-------------------|---------------|
| DRAFT | Любой editor | Полное редактирование |
| IN_REVIEW | Editor отправляет | Только комментарии, без правок |
| APPROVED | Reviewer | Export разрешён |
| EXPORTED | Автоматически после export | PNG/SVG файлы сгенерированы |
| PUBLISHED | Admin через Publish endpoint | Виден на публичном сайте |
| UNPUBLISHED | Admin | Снят с сайта, остаётся в архиве |

### 14.2 Version history

Каждое сохранение создаёт версию:

```json
{
  "version": 3,
  "savedAt": "2026-04-15T12:30:00Z",
  "savedBy": "admin",
  "changesSummary": "Updated headline, changed palette to energy",
  "documentSnapshot": { ... }
}
```

v1: последние 10 версий хранятся в `visual_config` history.
v2: полноценный version diff с rollback.

### 14.3 Система ролей (минимальная)

| Роль | Permissions |
|------|-------------|
| `editor` | Template mode. Создаёт/редактирует контент. Не может менять тему, сетку, brand tokens |
| `reviewer` | Может approve/reject. Не может редактировать |
| `admin` | Design mode. Полный доступ. Publish/unpublish. Управление темами и шаблонами |

v1: только admin (ты). Роли как архитектурная подготовка.
v2: editor + reviewer когда появится команда.

---

## 15. QA Layer (Editor = контролёр качества)

### 15.1 Validation панель (нижняя часть экрана)

Editor показывает не только layers, а ещё:

```
┌─────────────────────────────────────────────────────┐
│  QUALITY CHECK                                       │
│                                                      │
│  ✅ Source attribution present                       │
│  ✅ Brand stamp present                              │
│  ⚠️  Headline: 72/80 chars (close to limit)         │
│  ❌ Text overflow: subtitle exits safe zone          │
│  ⚠️  Contrast: 3.8:1 on gradient area (need 4.5:1)  │
│  ✅ Export-safe: all elements within bounds           │
│                                                      │
│  Status: 1 error, 2 warnings — FIX BEFORE EXPORT    │
└─────────────────────────────────────────────────────┘
```

### 15.2 Категории проверок

**Errors (блокируют export):**
- Text overflow за пределы canvas
- Missing source_footer
- Missing brand_stamp
- Contrast ratio < 3:1

**Warnings (не блокируют, но показываются):**
- Headline > 60 chars
- Contrast ratio < 4.5:1
- Missing subtitle
- Empty callout_box
- > 25 ranked items
- Missing delta_badge на hero_stat
- Gradient area с плохой читаемостью текста

**Info:**
- Character count per block
- Current export dimensions
- Layer count
- Data binding status

### 15.3 Export-safe indicator

В top bar рядом с Export кнопкой — индикатор:

- 🟢 **Ready** — 0 errors, 0 warnings
- 🟡 **Warnings** — 0 errors, N warnings
- 🔴 **Not ready** — N errors

Export кнопка disabled при 🔴.

---

## 16. Tooling Strategy

### 16.1 Разделение инструментов

| Инструмент | Роль | Когда |
|-----------|------|-------|
| **Claude Artifacts** | Design lab. Прототипирование шаблонов, блоков, стилей. Итерация через React/SVG/Canvas | При создании новых шаблонов, exploration стилистики |
| **React Editor** | Production tool. Ежедневная генерация инфографик. Контроль качества | Каждый день, основной workflow |
| **Illustrator / Photoshop** | Редкие исключения. Сложная иллюстрация, hero asset, нестандартный коллаж | < 5% случаев |

### 16.2 Workflow: новый шаблон

1. **Claude Artifact** — прототип нового шаблона/блока. Итерация дизайна
2. **Утверждение** — визуал одобрен
3. **Block definition** — JSON schema + renderer + inspector config
4. **Block registry** — регистрация в `blockRegistry`
5. **Template** — композиция блоков в шаблон
6. **Editor** — шаблон доступен для production использования

### 16.3 Почему не Figma

- Figma отлично подходит для design system exploration, но для production infographic generation — overhead
- Claude Artifacts дают live preview + итерацию за минуты
- React Editor = production environment, а не дизайн-инструмент
- Единый tech stack: React/TypeScript/Canvas на всех этапах

---

## 17. Расширенный набор шаблонов (8 семейств × 2-3 варианта)

Вместо 6 фиксированных шаблонов — 8 семейств, каждое с вариантами:

| # | Семейство | Вариант A | Вариант B | Вариант C |
|---|-----------|-----------|-----------|-----------|
| 1 | **Single Stat Hero** | Число + delta | Число + mini chart | Число + context paragraph |
| 2 | **Comparison** | 2 KPI side-by-side | 3 KPI row | Before/After |
| 3 | **Ranked Bars** | Simple (10-15) | Extended (20-30) | With benchmark line |
| 4 | **Dual Ranking** | Growth vs Decline | Two categories | Divergent bars |
| 5 | **Line Editorial** | Single series + area | Multi-line (2-3) | Annotated timeline |
| 6 | **Small Multiples** | 2×3 grid | 3×4 grid | 2×5 strip |
| 7 | **Visual Table** | Heatmap table | Ranked with scores | Multi-attribute |
| 8 | **Insight Card** | Quote + stat | Fact + mini chart | CTA + key number |

Итого: **8 семейств × ~2.5 варианта = ~20 production шаблонов** без хаоса.

Каждый вариант — это тот же набор блоков, но с разной default composition и разными locked zones.

---

## 18. Roadmap (обновлённый)

### v1 — Рабочий MVP

- Editor shell (top bar, left tabs, center canvas, right inspector, **QA panel**)
- Document model (project → page → section → block)
- 26 блоков
- **8 семейств шаблонов (~20 вариантов)**
- **Template mode + Design mode** (Editor mode — v2)
- **Lockable zones** (grid, safe margins, brand, source)
- **Content constraints** (char limits, overflow warnings, real-time counters)
- **QA layer** (validation panel, export-safe indicator)
- Theme presets (dark/light, 6 палитр)
- Manual data entry
- Export PNG (7 size presets)
- Save/Publish to backend
- **Document workflow: DRAFT → PUBLISHED** (IN_REVIEW/APPROVED — v2)
- **Version history** (last 10 saves)
- Gallery on real API (D-1)
- Lead capture flow (D-2)
- First distribution (D-5)

### v2 — Production editor

- **Editor mode** (intermediate access level)
- **Reviewer role** + IN_REVIEW/APPROVED workflow
- Drag-and-drop блоков (dnd-kit)
- Undo/redo (command system)
- CSV/JSON data paste → auto chart
- Data bindings to StatCan datasets
- Tier 2 шаблоны (Sankey, Treemap, Illustrated, Combo)
- Reusable custom templates
- Multi-page projects
- SVG export
- Template gallery
- **AI copy-fit** (Gemini headline suggestions, auto-shorten)
- **Accessibility auto-check** (contrast on gradient, mobile readability)
- **Full version diff + rollback**
- **Batch export** (multiple presets at once)

### v3 — Scale

- Maps (Tier 3) — TopoJSON, Canadian provinces
- Collaborative comments
- AI-assisted content fit (Gemini headline suggestions)
- Version history
- Brand kits (custom themes)
- Smart resize (auto-adapt to different size presets)
- PDF export
- Content warnings
- Layout suggestions

---

## 13. Цветовая система (из Design System v3.2 + SV Public)

### 13.1 Editor / Infographic (Dark mode — primary)

Используется Design System v3.2 — tokeny из CSS Reference Implementation. Источник правды: `DESIGN_SYSTEM_v3_2.md`.

### 13.2 Public site (Light + Dark)

Dual theme per SV Public Design document:

**Light:**
- Background: #F7F6F2 | Surface: #FFFFFF | Primary: #0A5E6C (Deep Teal)
- Text: #1A1A1A | Secondary: #555555 | Muted: #8A8A8A

**Dark:**
- Background: #111111 | Surface: #1A1A1A | Primary: #3AAFBF (Light Teal)
- Text: #E5E5E5 | Secondary: #B0B0B0 | Muted: #707070

### 13.3 Data visualization palette (sequential)

7 категорийных цветов (из SV Public doc): Deep Teal → Terra → Midnight → Ice → Mauve → Gold → Olive

---

## 14. Типографика

### 14.1 Инфографики (из Design System v3.2)

- Display: Bricolage Grotesque (700, 600)
- Body: DM Sans (400, 500)
- Data: JetBrains Mono (500, 700)

### 14.2 Public site (из SV Public doc)

- Display: General Sans (500-700, Fontshare)
- Body: Inter (400-600, Google Fonts)
- Data: JetBrains Mono (400)

### 14.3 Разделение

Инфографики и публичный сайт могут использовать разные шрифтовые пары. Инфографики — бренд Summa Vision (Bricolage + DM Sans). Сайт — оптимизирован для чтения (General Sans + Inter). Это нормально — VC тоже использует разные шрифты в инфографиках и на сайте.

---

*Документ является рабочим справочником. Обновляется при изменениях архитектуры редактора, добавлении блоков/шаблонов, или по результатам user testing.*
