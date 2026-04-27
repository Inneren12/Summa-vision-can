# Summa Vision — Design System v3.2

**Статус:** Production-ready for v1 implementation, with extension points for localization, uncertainty encoding, and advanced chart interaction.  
**Платформы:** Next.js (public site), Flutter (admin panel), Plotly / D3 / Visx (chart generation), PNG/SVG export (social media).  
**Оптимизировано для:** Canvas/SVG charts, mobile devices, public storytelling, dense analytical dashboards, social distribution.

---

## Содержание

1. [Визуальная философия](#блок-1-визуальная-философия-и-бренд)
2. [Типографика](#блок-2-типографика)
3. [Цветовая система (4-слойные токены)](#блок-3-цветовая-система)
4. [Компоненты UI](#блок-4-архитектура-компонентов)
5. [Аналитические таблицы](#блок-5-аналитические-таблицы)
6. [Responsive, Density & Modes](#блок-6-responsive-density--modes)
7. [Анимация](#блок-7-анимация-и-переходы)
8. [Accessibility & Data Legibility](#блок-8-accessibility--data-legibility)
9. [Data Viz Canon](#блок-9-data-visualization-canon)
10. [Data Reliability & Uncertainty](#блок-10-data-reliability--uncertainty)
11. [Social Media Export Rules](#блок-11-social-media-export-rules)
12. [Content Hierarchy Rules](#блок-12-content-hierarchy-rules)
13. [Layering & Elevation](#блок-13-layering--elevation)
14. [Localization & Formatting Policy](#блок-14-localization--formatting-policy)
15. [Запреты](#блок-15-запреты-anti-patterns)
16. [CSS Reference Implementation](#блок-16-css-reference-implementation)
17. [Flutter Token Mapping](#блок-17-flutter-token-mapping)
18. [Versioning & Change Policy](#блок-18-versioning--change-policy)

---

## БЛОК 1: Визуальная философия и Бренд

### Позиционирование: Premium Investigative Data Publication

Не Bloomberg-терминал. Не news outlet.  
**Forensic public finance platform** с editorial качеством визуализаций.

### Стиль: "Analytical Noir" / "Tactical Minimalism"

Скрещивание архитектурной строгости The Economist, тактильности Bloomberg Dark UI и типографической дисциплины Stripe.

### Принципы

**Data is the only light source.**  
Данные — единственный источник света на экране.

**Brand and UI must never outrank the data layer.**  
Ни бренд, ни декоративный UI не должны перетягивать визуальный приоритет у графика, таблицы или цифры.

**Экстремальный Data-Ink Ratio.**  
Удаляем всё, что не несёт информационного веса: лишние сетки, рамки, шумовые заливки, декоративные градиенты.

**Скевоморфизм данных.**  
Жёсткие сетки, табличные цифры и моноширинный слой создают ощущение "сырых данных из базы", а не маркетинговой инфографики.

**Отрицательное пространство.**  
Grid 8pt. Воздух не украшает, а изолирует инсайты.

**Forensic, не polemic.**  
Визуальный язык должен транслировать независимость и доказательность, а не агитацию.

---

## БЛОК 2: Типографика

3-уровневая система (Google Fonts), нативно встраиваемая во Flutter (`google_fonts`) и Next.js (`next/font/google`).

**Глобальное правило:** `font-feature-settings: "tnum";` — tabular numbers everywhere.

### Dual Typography Mode

Два режима использования display-шрифта.

| Режим | Где применяется | Display font | H2 / H3 |
|------|------------------|--------------|---------|
| **Editorial** | Landing, share cards, Signal exports, public hero sections | Bricolage Grotesque | Bricolage Grotesque |
| **Operational** | Dense dashboards, admin panel, methodology, tables | Bricolage Grotesque только для Hero KPI | DM Sans SemiBold |

**Правило переключения:**  
Если на экране > 3 data cards, > 2 charts одновременно, или экран primarily operational — используется **Operational mode**.

### 1. Display — Bricolage Grotesque

| Роль | Desktop | Mobile | Вес | Line-height | Letter-spacing |
|------|---------|--------|-----|-------------|----------------|
| Hero KPI | 64px / 4rem | 40px / 2.5rem | 700 | 100% | -0.03em |
| H1 | 36px / 2.25rem | 26px / 1.625rem | 600 | 110% | -0.02em |
| H2 (Editorial) | 24px / 1.5rem | 20px / 1.25rem | 600 | 120% | -0.01em |
| H3 (Editorial) | 20px / 1.25rem | 18px / 1.125rem | 600 | 130% | 0 |

### 2. Body — DM Sans

| Роль | Desktop | Mobile | Вес | Line-height |
|------|---------|--------|-----|-------------|
| Lead | 18px / 1.125rem | 16px / 1rem | 500 | 150% |
| Body | 16px / 1rem | 15px / 0.9375rem | 400 | 160% |
| Caption | 14px / 0.875rem | 13px / 0.8125rem | 400 | 150% |
| UI Label | 14px / 0.875rem | 14px | 500 | 100% |
| H2 (Operational) | 22px / 1.375rem | 19px / 1.1875rem | 600 | 125% |
| H3 (Operational) | 18px / 1.125rem | 16px / 1rem | 600 | 135% |

### 3. Data — JetBrains Mono

| Роль | Desktop | Mobile | Вес | Line-height | Доп. стили |
|------|---------|--------|-----|-------------|------------|
| Axis Labels | 12px | 11px | 500 | 130% | UPPERCASE, ls: +0.05em |
| Tooltip Values | 14px | 13px | 700 | 120% | — |
| Table Data | 14px | 13px | 400 | 140% | `tnum` |
| Eyebrow | 11px | 10px | 500 | 100% | UPPERCASE, ls: +0.08em |
| Source Line | 10px–12px | 10px–11px | 500 | 130% | `tnum`, muted |

---

## БЛОК 3: Цветовая система

4-слойная иерархия: **Foundation → Semantic UI → Data Semantic → Component**.

### Layer 1: Foundation (raw values)

Никогда не используются напрямую в компонентах.

```css
--raw-slate-950:    #0B0D11;
--raw-slate-900:    #15181E;
--raw-slate-850:    #1C1F26;
--raw-slate-800:    #262A33;
--raw-slate-600:    #5C6370;
--raw-slate-400:    #8B949E;
--raw-slate-100:    #F3F4F6;
--raw-white:        #FAFBFC;

--raw-gold-500:     #FBBF24;
--raw-gold-600:     #F59E0B;
--raw-gold-700:     #D97706;
--raw-gold-alpha:   rgba(251,191,36,0.15);

--raw-blue-500:     #3B82F6;
--raw-lavender-400: #A78BFA;
--raw-teal-400:     #2DD4BF;
--raw-orange-500:   #F97316;
--raw-silver-400:   #94A3B8;
--raw-cyan-400:     #22D3EE;

--raw-red-900:      #7F1D1D;
--raw-red-500:      #E11D48;
--raw-green-900:    #064E3B;
--raw-green-500:    #0D9488;
Layer 2: Semantic UI
Dark Mode (основной)
Token	Применение
--bg-app	App background
--bg-surface	Cards, panels
--bg-surface-hover	Hover
--bg-surface-active	Pressed / selected
--border-default	Dividers
--border-subtle	Inner stroke
--border-focus	Focus ring
--text-primary	Main text
--text-secondary	Captions
--text-muted	Disabled
--text-inverse	Text on light tooltip / accent buttons
--accent	CTA, active controls
--accent-hover	Hover CTA
--accent-muted	Slider glow
--destructive	Errors / delete
Light Mode (только export)
Token	Значение
--bg-app	#FAFBFC
--bg-surface	#FFFFFF
--border-default	#E2E4E9
--text-primary	#111318
--text-secondary	#5C6370
--accent	#D97706
Layer 3: Data Semantic
Тематические data colors
Token	Hex	Семантика
--data-gov	#3B82F6	Government / fiscal
--data-society	#A78BFA	Demography / justice
--data-infra	#2DD4BF	Resources / energy
--data-monopoly	#F97316	Monopoly / transport
--data-baseline	#94A3B8	Benchmark / peers
--data-housing	#22D3EE	Housing / real estate
Sentiment
Token	Hex	Применение
--data-negative	#E11D48	Pain / loss
--data-negative-dark	#7F1D1D	Negative gradient start
--data-positive	#0D9488	Gain / surplus
--data-positive-dark	#064E3B	Positive gradient start
--data-warning	#F97316	Warning
--data-neutral	#262A33	Midpoint / zero-line
Chart Behavior Semantics

Этот слой отвечает не за тему данных, а за поведение ряда.

Token	Назначение
--series-primary	Главный ряд
--series-secondary	Вторичный ряд
--series-benchmark	Benchmark / peer / national average
--series-forecast	Projection / forecast
--series-selected	Активно выбранный ряд
--series-muted	Отфильтрованный / диммированный
--series-uncertainty-fill	Confidence band / range

Правило:
Тематический цвет и поведенческая роль комбинируются, а не заменяют друг друга.

Layer 4: Component Tokens
Token	Применение
--card-bg	Card fill
--card-border	Card border
--tooltip-bg	Tooltip fill
--tooltip-text	Tooltip primary text
--tooltip-label	Tooltip secondary text
--btn-primary-bg	CTA
--btn-primary-text	CTA text
--btn-primary-bg-hover	CTA hover
--toggle-active-bg	Active toggle tab
--toggle-active-text	Active text
--toggle-inactive-text	Inactive text
--slider-track	Slider track
--slider-thumb	Slider thumb
--slider-glow	Slider glow
--input-bg	Input bg
--input-border	Input border
--input-border-focus	Input focus border
--input-text	Input text
--input-placeholder	Placeholder
БЛОК 4: Архитектура компонентов
4.1 Component State Matrix

Все интерактивные элементы обязаны иметь состояния:
default / hover / pressed / focused / disabled / loading / selected.

Button (Primary)
State	Background	Text	Border	Focus ring	Shadow
Default	--accent	--text-inverse	none	none	none
Hover	--accent-hover	--text-inverse	none	none	0 4px 12px rgba(251,191,36,0.2)
Pressed	#D97706	--text-inverse	none	none	none
Focused	--accent	--text-inverse	none	double ring	none
Disabled	rgba(251,191,36,0.3)	rgba(11,13,17,0.5)	none	none	none
Loading	--accent at 60%	Spinner inverse	none	none	none
Button (Secondary)
State	Background	Text	Border	Focus ring
Default	transparent	--text-primary	1px solid var(--border-default)	none
Hover	--bg-surface-hover	--text-primary	1px solid var(--text-secondary)	none
Pressed	--bg-surface-active	--text-primary	1px solid var(--text-secondary)	none
Focused	transparent	--text-primary	1px solid var(--border-default)	double ring
Disabled	transparent	--text-muted	1px solid rgba(38,42,51,0.5)	none
Toggle / Segmented Control
State	Background	Text	Border
Inactive	transparent	--text-muted	none
Hover	rgba(255,255,255,0.03)	--text-secondary	none
Active	--border-default	--text-primary	1px solid rgba(255,255,255,0.15)
Focused	same	same	same + focus ring
Disabled	transparent	rgba(92,99,112,0.5)	none
Slider
State	Track	Thumb	Glow	Focus ring
Default	--border-default	#FFFFFF	none	none
Hover	--border-default	#FFFFFF	0 0 0 6px var(--accent-muted)	none
Dragging	active fill --accent	#FFFFFF	0 0 0 8px var(--accent-muted)	none
Focused	--border-default	#FFFFFF	none	double ring
Disabled	rgba(38,42,51,0.3)	--text-muted	none	none
Input / Select
State	Border	Background	Text
Default	--border-default	--bg-surface	--text-primary
Hover	--text-secondary	--bg-surface	--text-primary
Focused	--accent 2px	--bg-surface	--text-primary
Error	--data-negative	--bg-surface	--text-primary
Disabled	rgba(38,42,51,0.3)	rgba(21,24,30,0.5)	--text-muted
Chart Interaction States
State	Поведение
Default	Все серии normal
Hover	Hovered series full opacity, others 0.25
Selected	Selected series full opacity + thicker stroke
Muted	0.2 opacity
Tooltip active	Crosshair line + point marker
Keyboard focus	Point/segment gets visible ring or halo
4.2 Data Cards
Свойство	Admin	Public	Export
Fill	--bg-surface	--bg-surface	--bg-surface / light
Border	inset subtle	inset subtle	1px solid --border-default
Radius	4px	10px	10px
Padding	20px	24px / 16px mobile	40px–56px

Layout:
Hero KPI — строго левый верхний угол.
Под KPI — underline 2px --accent.
Один data card = один underline maximum.

4.3 Tooltip
Свойство	Значение
Background	--tooltip-bg
Value text	JetBrains Mono 14px Bold
Label text	DM Sans 12px
Radius	4px
Max-width	240px
Padding	10px 14px
Shadow	--shadow-tooltip

Поведение:

150ms, no bounce
offset 8px+
flip logic required
mobile = tap-lock
dense charts > 6 series = aggregated tooltip
tooltip never the only place where critical value exists
4.4 Buttons
Тип	Фон	Текст	Radius
Primary	--accent	--text-inverse	8px public / 4px admin
Secondary	transparent	--text-primary	8px / 4px
Ghost	transparent	--text-secondary	none
Destructive	--destructive	#FFFFFF	8px / 4px

Min height: 36px desktop, 44px mobile.

БЛОК 5: Аналитические таблицы

Таблицы — доказательный слой платформы.

Table Style
Свойство	Значение
Header bg	--bg-surface-hover
Header text	DM Sans 12px SemiBold UPPERCASE
Row bg even	--bg-surface
Row bg odd	--bg-app
Row hover	--bg-surface-hover
Row selected	rgba(251,191,36,0.06)
Cell text	JetBrains Mono 14px / 13px mobile
Cell padding	density-based
Sticky header	always sticky
Sticky header shadow	bottom shadow on scroll
Numeric Formatting
Rule	Behaviour
Numeric columns	right-aligned
Text columns	left-aligned
Negative numbers	--data-negative, no parentheses
Delta cells	arrow + value
Thousands	locale-based
Abbreviations	K, M, B, T
Currency	use currency prefix consistently
Null/missing	em dash —
Suppressed	diagonal hatching 45° bg + × marker, --border-default at 0.3 opacity. Distinct from null (em dash) and zero.
Sort Indicators
State	Visual
Sortable	subtle ↕
Asc	↑
Desc	↓
БЛОК 6: Responsive, Density & Modes
Breakpoints
Token	Width
--bp-mobile	< 640px
--bp-tablet	640–1023px
--bp-desktop	1024–1439px
--bp-wide	≥ 1440px
Density Modes
Token	Comfortable	Compact	Dense
--space-xs	4px	3px	2px
--space-sm	8px	6px	4px
--space-md	16px	12px	8px
--space-lg	24px	18px	12px
--space-xl	32px	24px	16px
--space-2xl	48px	36px	24px
--space-3xl	64px	48px	32px

Правило:
Public site = Comfortable only.
Admin = Comfortable default, Compact optional.
Dense = special analytical views / export prep only.

Chart Modes
Editorial Chart Mode

Для public storytelling.

Параметр	Значение
Series max	3
Annotation max	5
Direct labels	preferred
Axes density	sparse
Headline weight	high
Caption	always visible
Benchmark lines	subtle
Operational Chart Mode

Для admin / internal analysis.

Параметр	Значение
Series max	6
Annotation max	2
Direct labels	optional
Axes density	denser
Tooltip	compact, data-first
Table pairing	encouraged
Benchmark/reference	more visible
Chart Sizing
Контекст	Width	Height	Padding
Full-width desktop	100%	480px	24px
Full-width mobile	100%	320px	16px
Card embedded desktop	100%	280px	16px
Card embedded mobile	100%	200px	12px
Signal Reddit/X	1200×900	—	48–56px
Signal Instagram	1080×1350	—	40–48px
Signal X wide	1200×675	—	40–48px
Touch Targets
Элемент	Min size
Button	44px height
Slider thumb	24px visible / 44px touch
Toggle	44px
Link target	44×44px
Tooltip trigger	32×32px
БЛОК 7: Анимация и переходы

Анимация не украшает, а объясняет дельту.

Easing
cubic-bezier(0.16, 1, 0.3, 1)
Timing
Категория	Duration
Micro	150ms
Data	400ms
Page	800ms
Stagger	30ms
Разрешённые data motions
Number rolling
Staggered bars / nodes
Path morphing between states
Skeleton shimmer instead of spinners
Запрещено
bounce
elastic
cartoon spring on charts
spin loader over chart canvas
parallax on data pages
Reduced Motion
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
БЛОК 8: Accessibility & Data Legibility
Контраст

Все ключевые пары обязаны соответствовать минимум AA, основные пары — AAA.

Focus Ring
:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--bg-app), 0 0 0 4px var(--accent);
}
Non-Color Encoding

Смысл никогда не передаётся только цветом.

Chart type	Цвет	Обязательный дублёр
Line	color	dash style и/или direct label
Bar	color	value label или category axis
Heatmap	gradient	numeric annotation
Donut	color	direct label
Scatter	color	marker shape
Sankey	color	node label
Keyboard Navigation
sliders: arrows, shift+arrows
toggles: left/right
chart points: tab / arrows / enter
tooltips callable without mouse
Screen Reader
charts get aria-label
tables use semantic HTML
KPI cards with dynamic values use aria-live="polite"
SR Fallback for Canvas/SVG

Сложные charts могут быть aria-hidden="true" только если рядом есть .sr-only table with raw values.

БЛОК 9: Data Visualization Canon
9.1 Общие правила
Элемент	Толщина / стиль	Opacity
Primary line	2px	1.0
Secondary line	1.5px	0.72
Benchmark	1px dashed	0.6
Forecast	1px dotted	0.5
Zero line	1px solid	1.0
Grid lines	1px solid	0.15
Axis lines	1px solid	0.4
Numbers & Labels
Rule	Format
Thousands	47,000 or locale equivalent
Millions	4.2M
Billions	1.3B
Trillions	2.1T
Percent	47.6%
Negative	true minus −$4,200
Year	2025
Month public	Jan 2025
Month dense	2025-01
Axis density	max 7 labels
General Constraints
Rule	Value
Visible series without interaction	4
With toggle/legend	8
Caption	required
Source attribution	required
Annotations	max 5 editorial / 2 operational
Legend	direct label preferred
9.2 Line Charts
2px primary
markers hidden by default
direct label on last point preferred
divergence fills allowed at low opacity
spline smoothing forbidden for observed discrete data (prices, rates, counts). Allowed for continuous model outputs (METR curves, projections) where the line represents a calculated function, not observed data points.
9.3 Bar Charts
zero baseline mandatory
gap ratio 0.3
2px top radius only
grouped max 4 per group
if labels long → horizontal bar
truncated Y-axis forbidden
9.4 Area Charts
fill opacity 0.15
zero baseline mandatory
stacked max 5 layers
9.5 Scatter
marker size 6px default
max 500 points without sampling
trend line optional, subtle
9.6 Heatmaps / Choropleths
negative → neutral → positive
direct red→green forbidden
key cells must carry numeric annotation
missing data visibly distinct
9.7 Sankey
max 8 nodes per column
min link thickness 2px
sort by value descending
label truncation max 20 chars + ellipsis
9.8 Donut

Allowed only for share-of-total with ≤ 5 segments and one dominant message.

9.9 Slope

For exactly two time points. Endpoint labels mandatory.

9.10 Waterfall

Use for decomposition only.

Rule	Value
Start / end bars	stronger emphasis
Intermediate bars	neutral or signed semantic
Connector lines	1px subtle
Max steps	8
9.11 Small Multiples

Use when single chart gets cluttered.

Rule	Value
Shared axis scale	mandatory
Max panels per row	4
Same chart type	mandatory
Same ordering	mandatory
БЛОК 10: Data Reliability & Uncertainty

Этот блок обязателен для forensic credibility.

Reliability States
Состояние	Визуал
Final / observed	solid line, full opacity
Preliminary	solid line + PRELIMINARY tag
Revised	footnote marker † + revision note
Forecast / projected	dotted line, opacity 0.5, explicit label
Estimate	dashed line, opacity 0.7
Confidence interval	subtle band, opacity 0.12
Range / uncertainty	band fill --series-uncertainty-fill
Suppressed	diagonal hatching 45° in --border-default at 0.3 opacity + × marker in cell center (tables) or Suppressed label (charts). Pattern: repeating-linear-gradient(45deg, var(--suppressed-pattern-color) 1px, transparent 1px) with --suppressed-pattern-spacing gap. This follows StatCan/CMHC convention for confidentiality-suppressed data.
Missing	em dash —
Not applicable	N/A only in backend/admin, never in public-facing charts
Rules

Forecasts must always be labeled.
Никаких unlabeled dotted tails.

Revisions must be visible.
Если data series revised after publication, chart or caption must indicate it.

Missing and suppressed are not the same.
Пустая ячейка, suppressed cell и truly missing value визуально различаются.

Confidence is never implied by color intensity alone.
Use band, label, or note.

БЛОК 11: Social Media Export Rules
Safe Areas
Зона	Значение
Top safe	48px
Bottom safe	80px
Left / right	48px
Instagram story top	120px
Instagram story bottom	100px
Per Platform
Platform	Format	Max series	Min font	Preferred mode
Reddit	1200×900	2	12px	Dark
X	1200×675	2	13px	Dark
Instagram Feed	1080×1350	1	14px	Dark/Light
Instagram Story	1080×1920	1	16px	Dark
LinkedIn	1200×627	3	12px	Light preferred
Fixed Export Anatomy
Элемент	Позиция	Стиль
Category tag	top-left	JetBrains Mono
Hook headline	top-left main area	Bricolage 48px editorial
Main chart	center	60%+ visual area
Brand name	bottom-right	secondary, but legible
Source line	bottom-left/bottom strip	required
Methodology	not in image by default	in post copy
Export Governance
Export without source line is blocked
Watermark must never overlap main chart marks
Source line opacity must remain legible after social recompression
One export = one insight, one chart, one hero number maximum
БЛОК 12: Content Hierarchy Rules

1. Один Hero KPI на экран.
Остальные метрики secondary.

2. Один brand underline на карточку.
И не более одного главного underline на ключевой insight cluster.

3. Два уровня типографического акцента max внутри одной card.

4. Chart = caption.
Без source/caption chart не публикуется.

5. Brand accent точечно.
Gold only for CTA, active controls, KPI underline, slider glow.

6. One screen = one primary argument.
Если экран доказывает больше одной мысли, он распался концептуально.

7. Methodology belongs to footer zone.
Главный storytelling — сверху, методология — внизу.

БЛОК 13: Layering & Elevation

Нужен фиксированный слой порядка.

Layer	z-index	Use
Base content	0	cards, charts, tables
Sticky headers	10	sticky table headers, docked controls
Chart overlays	20	crosshair, active point, annotation hover
Popovers / menus	30	dropdowns, contextual menus
Tooltips	40	chart tooltips
Modals / drawers	50	dialogs, side panels
Blocking alerts	60	critical alerts
Rules
Tooltip always above chart overlay
Sticky header never above modal
Export watermark stays below tooltip layer in interactive mode
Flutter implementation must mirror layer intent even if actual API differs
БЛОК 14: Localization & Formatting Policy
Locale Policy
Context	Default
Public site	en-CA
Admin panel	en-CA initially
Future extension	fr-CA
Formatting Rules
Use one locale system per screen
Currency with ambiguity must be explicit: CA$
Negative values use true minus −, not hyphen -
Public month style: Jan 2026
Dense/admin month style: 2026-01
No mixing commas and thin spaces on same screen
K/M/B/T abbreviations allowed only if consistent within context
Number Semantics
Type	Rule
Currency > 1000	no cents
Currency < 100	cents allowed
Percent	max 1 decimal
Rate / ratio	up to 2 decimals
Null	em dash
Suppressed	labeled as suppressed
Approximate	prefix/suffix or note, never silent rounding
БЛОК 15: Запреты (Anti-Patterns)
Категория	Запрещено	Почему
Effects	Glassmorphism	FPS death
Effects	pure #000000 bg	halo fatigue
Effects	pure #FFFFFF text	too harsh
Effects	gradient card backgrounds	visual noise
Color	traffic-light red/green	cheap + accessibility issues
Color	brand gold in charts	false semantic emphasis
Color	meaning by color alone	accessibility fail
Typography	Inter / Roboto / Arial / Space Grotesk	generic
Radius	> 12px	breaks tone
Animation	bounce / elastic on data	unserious
Charts	3D charts	lie factor
Charts	pie > 5 segments	unreadable
Charts	truncated Y-axis on bars	misleading
Charts	smoothed spline on financial data	distorts truth
Charts	unlabeled forecast lines	deceptive
Charts	hidden axis/domain truncation	misleading
Charts	dual Y-axis by default	correlation confusion
Layout	centered KPI	wrong hierarchy
Layout	desktop carousels	hides data
Content	chart without source	no trust
Content	tooltip-only critical values	accessibility fail
БЛОК 16: CSS Reference Implementation
:root {
  --font-display: 'Bricolage Grotesque', system-ui, sans-serif;
  --font-body: 'DM Sans', system-ui, sans-serif;
  --font-data: 'JetBrains Mono', 'Fira Code', monospace;

  --raw-slate-950: #0B0D11;
  --raw-slate-900: #15181E;
  --raw-slate-850: #1C1F26;
  --raw-slate-800: #262A33;
  --raw-slate-600: #5C6370;
  --raw-slate-400: #8B949E;
  --raw-slate-100: #F3F4F6;

  --raw-gold-500: #FBBF24;
  --raw-gold-600: #F59E0B;
  --raw-gold-700: #D97706;
  --raw-gold-alpha: rgba(251,191,36,0.15);

  --bg-app: var(--raw-slate-950);
  --bg-surface: var(--raw-slate-900);
  --bg-surface-hover: var(--raw-slate-850);
  --bg-surface-active: #22252D;
  --border-default: var(--raw-slate-800);
  --border-subtle: rgba(255,255,255,0.06);
  --border-focus: rgba(251,191,36,0.45);

  --text-primary: var(--raw-slate-100);
  --text-secondary: var(--raw-slate-400);
  --text-muted: var(--raw-slate-600);
  --text-inverse: var(--raw-slate-950);

  --accent: var(--raw-gold-500);
  --accent-hover: var(--raw-gold-600);
  --accent-muted: var(--raw-gold-alpha);
  --destructive: #E11D48;

  --data-gov: #3B82F6;
  --data-society: #A78BFA;
  --data-infra: #2DD4BF;
  --data-monopoly: #F97316;
  --data-baseline: #94A3B8;
  --data-housing: #22D3EE;
  --data-negative: #E11D48;
  --data-negative-dark: #7F1D1D;
  --data-positive: #0D9488;
  --data-positive-dark: #064E3B;
  --data-warning: #F97316;
  --data-neutral: #262A33;

  /* ─── LAYER 3b: CHART BEHAVIOR TOKENS ─── */
  --series-primary-weight: 2px;
  --series-primary-opacity: 1.0;
  --series-secondary-weight: 1.5px;
  --series-secondary-opacity: 0.72;
  --series-benchmark-weight: 1px;
  --series-benchmark-style: dashed;
  --series-benchmark-opacity: 0.6;
  --series-forecast-weight: 1px;
  --series-forecast-style: dotted;
  --series-forecast-opacity: 0.5;
  --series-selected-weight: 3px;
  --series-selected-opacity: 1.0;
  --series-muted-opacity: 0.2;
  --series-hover-dim: 0.25;
  --series-uncertainty-fill-opacity: 0.12;
  --series-estimate-style: dashed;
  --series-estimate-opacity: 0.7;

  /* Suppressed data pattern */
  --suppressed-pattern-color: var(--border-default);
  --suppressed-pattern-opacity: 0.3;
  --suppressed-pattern-angle: 45deg;
  --suppressed-pattern-spacing: 6px;

  --card-bg: var(--bg-surface);
  --card-border: var(--border-subtle);
  --tooltip-bg: var(--text-primary);
  --tooltip-text: var(--text-inverse);
  --tooltip-label: #4B5563;
  --btn-primary-bg: var(--accent);
  --btn-primary-text: var(--text-inverse);

  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
  --space-3xl: 64px;

  --radius-admin: 4px;
  --radius-public: 10px;
  --radius-button: 8px;
  --radius-tooltip: 4px;

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-micro: 150ms;
  --duration-data: 400ms;
  --duration-page: 800ms;
  --stagger: 30ms;

  --shadow-card: inset 0 0 0 1px rgba(255,255,255,0.06);
  --shadow-tooltip: 0 12px 32px rgba(0,0,0,0.8);
  --shadow-elevated: 0 8px 24px rgba(0,0,0,0.4);

  --z-base: 0;
  --z-sticky: 10;
  --z-chart-overlay: 20;
  --z-popover: 30;
  --z-tooltip: 40;
  --z-modal: 50;
  --z-alert: 60;
}

body.density-compact {
  --space-xs: 3px;
  --space-sm: 6px;
  --space-md: 12px;
  --space-lg: 18px;
  --space-xl: 24px;
  --space-2xl: 36px;
  --space-3xl: 48px;
}

body.density-dense {
  --space-xs: 2px;
  --space-sm: 4px;
  --space-md: 8px;
  --space-lg: 12px;
  --space-xl: 16px;
  --space-2xl: 24px;
  --space-3xl: 32px;
}

.theme-light {
  --bg-app: #FAFBFC;
  --bg-surface: #FFFFFF;
  --border-default: #E2E4E9;
  --border-subtle: rgba(0,0,0,0.06);
  --text-primary: #111318;
  --text-secondary: #5C6370;
  --text-inverse: #FAFBFC;
  --accent: #D97706;
  --accent-hover: #B45309;
  --accent-muted: rgba(217,119,6,0.1);
}

:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--bg-app), 0 0 0 4px var(--accent);
}

@media (max-width: 640px) {
  :root {
    --space-md: 12px;
    --space-lg: 16px;
    --space-xl: 24px;
    --space-2xl: 32px;
    --space-3xl: 40px;
  }
}

@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

body {
  font-feature-settings: "tnum";
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
БЛОК 17: Flutter Token Mapping
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

final displayFont = GoogleFonts.bricolageGrotesque;
final bodyFont = GoogleFonts.dmSans;
final dataFont = GoogleFonts.jetBrainsMono;

enum DensityMode { comfortable, compact, dense }
enum ChartMode { editorial, operational }

@immutable
class SummaTheme extends ThemeExtension<SummaTheme> {
  // UI Semantic
  final Color bgApp;
  final Color bgSurface;
  final Color borderDefault;
  final Color textPrimary;
  final Color textSecondary;
  final Color textMuted;
  final Color accent;
  final Color destructive;

  // Data Semantic
  final Color dataGov;
  final Color dataSociety;
  final Color dataInfra;
  final Color dataMonopoly;
  final Color dataBaseline;
  final Color dataHousing;
  final Color dataNegative;
  final Color dataPositive;
  final Color dataWarning;
  final Color dataNeutral;

  // Chart Behavior
  final double seriesPrimaryWeight;
  final double seriesSecondaryWeight;
  final double seriesBenchmarkWeight;
  final double seriesForecastWeight;
  final double seriesMutedOpacity;
  final double seriesHoverDim;
  final double seriesUncertaintyFillOpacity;

  const SummaTheme({
    required this.bgApp,
    required this.bgSurface,
    required this.borderDefault,
    required this.textPrimary,
    required this.textSecondary,
    required this.textMuted,
    required this.accent,
    required this.destructive,
    required this.dataGov,
    required this.dataSociety,
    required this.dataInfra,
    required this.dataMonopoly,
    required this.dataBaseline,
    required this.dataHousing,
    required this.dataNegative,
    required this.dataPositive,
    required this.dataWarning,
    required this.dataNeutral,
    this.seriesPrimaryWeight = 2.0,
    this.seriesSecondaryWeight = 1.5,
    this.seriesBenchmarkWeight = 1.0,
    this.seriesForecastWeight = 1.0,
    this.seriesMutedOpacity = 0.2,
    this.seriesHoverDim = 0.25,
    this.seriesUncertaintyFillOpacity = 0.12,
  });

  static const dark = SummaTheme(
    bgApp: Color(0xFF0B0D11),
    bgSurface: Color(0xFF15181E),
    borderDefault: Color(0xFF262A33),
    textPrimary: Color(0xFFF3F4F6),
    textSecondary: Color(0xFF8B949E),
    textMuted: Color(0xFF5C6370),
    accent: Color(0xFFFBBF24),
    destructive: Color(0xFFE11D48),
    dataGov: Color(0xFF3B82F6),
    dataSociety: Color(0xFFA78BFA),
    dataInfra: Color(0xFF2DD4BF),
    dataMonopoly: Color(0xFFF97316),
    dataBaseline: Color(0xFF94A3B8),
    dataHousing: Color(0xFF22D3EE),
    dataNegative: Color(0xFFE11D48),
    dataPositive: Color(0xFF0D9488),
    dataWarning: Color(0xFFF97316),
    dataNeutral: Color(0xFF262A33),
    // Chart behavior tokens use defaults from constructor
  );

  @override
  SummaTheme copyWith({
    Color? bgApp, Color? bgSurface, Color? borderDefault,
    Color? textPrimary, Color? textSecondary, Color? textMuted,
    Color? accent, Color? destructive,
    Color? dataGov, Color? dataSociety, Color? dataInfra,
    Color? dataMonopoly, Color? dataBaseline, Color? dataHousing,
    Color? dataNegative, Color? dataPositive, Color? dataWarning, Color? dataNeutral,
    double? seriesPrimaryWeight, double? seriesSecondaryWeight,
    double? seriesBenchmarkWeight, double? seriesForecastWeight,
    double? seriesMutedOpacity, double? seriesHoverDim,
    double? seriesUncertaintyFillOpacity,
  }) {
    return SummaTheme(
      bgApp: bgApp ?? this.bgApp,
      bgSurface: bgSurface ?? this.bgSurface,
      borderDefault: borderDefault ?? this.borderDefault,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textMuted: textMuted ?? this.textMuted,
      accent: accent ?? this.accent,
      destructive: destructive ?? this.destructive,
      dataGov: dataGov ?? this.dataGov,
      dataSociety: dataSociety ?? this.dataSociety,
      dataInfra: dataInfra ?? this.dataInfra,
      dataMonopoly: dataMonopoly ?? this.dataMonopoly,
      dataBaseline: dataBaseline ?? this.dataBaseline,
      dataHousing: dataHousing ?? this.dataHousing,
      dataNegative: dataNegative ?? this.dataNegative,
      dataPositive: dataPositive ?? this.dataPositive,
      dataWarning: dataWarning ?? this.dataWarning,
      dataNeutral: dataNeutral ?? this.dataNeutral,
      seriesPrimaryWeight: seriesPrimaryWeight ?? this.seriesPrimaryWeight,
      seriesSecondaryWeight: seriesSecondaryWeight ?? this.seriesSecondaryWeight,
      seriesBenchmarkWeight: seriesBenchmarkWeight ?? this.seriesBenchmarkWeight,
      seriesForecastWeight: seriesForecastWeight ?? this.seriesForecastWeight,
      seriesMutedOpacity: seriesMutedOpacity ?? this.seriesMutedOpacity,
      seriesHoverDim: seriesHoverDim ?? this.seriesHoverDim,
      seriesUncertaintyFillOpacity: seriesUncertaintyFillOpacity ?? this.seriesUncertaintyFillOpacity,
    );
  }

  @override
  SummaTheme lerp(ThemeExtension<SummaTheme>? other, double t) {
    if (other is! SummaTheme) return this;
    return SummaTheme(
      bgApp: Color.lerp(bgApp, other.bgApp, t)!,
      bgSurface: Color.lerp(bgSurface, other.bgSurface, t)!,
      borderDefault: Color.lerp(borderDefault, other.borderDefault, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      textMuted: Color.lerp(textMuted, other.textMuted, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      destructive: Color.lerp(destructive, other.destructive, t)!,
      dataGov: Color.lerp(dataGov, other.dataGov, t)!,
      dataSociety: Color.lerp(dataSociety, other.dataSociety, t)!,
      dataInfra: Color.lerp(dataInfra, other.dataInfra, t)!,
      dataMonopoly: Color.lerp(dataMonopoly, other.dataMonopoly, t)!,
      dataBaseline: Color.lerp(dataBaseline, other.dataBaseline, t)!,
      dataHousing: Color.lerp(dataHousing, other.dataHousing, t)!,
      dataNegative: Color.lerp(dataNegative, other.dataNegative, t)!,
      dataPositive: Color.lerp(dataPositive, other.dataPositive, t)!,
      dataWarning: Color.lerp(dataWarning, other.dataWarning, t)!,
      dataNeutral: Color.lerp(dataNeutral, other.dataNeutral, t)!,
      seriesPrimaryWeight: lerpDouble(seriesPrimaryWeight, other.seriesPrimaryWeight, t)!,
      seriesSecondaryWeight: lerpDouble(seriesSecondaryWeight, other.seriesSecondaryWeight, t)!,
      seriesBenchmarkWeight: lerpDouble(seriesBenchmarkWeight, other.seriesBenchmarkWeight, t)!,
      seriesForecastWeight: lerpDouble(seriesForecastWeight, other.seriesForecastWeight, t)!,
      seriesMutedOpacity: lerpDouble(seriesMutedOpacity, other.seriesMutedOpacity, t)!,
      seriesHoverDim: lerpDouble(seriesHoverDim, other.seriesHoverDim, t)!,
      seriesUncertaintyFillOpacity: lerpDouble(seriesUncertaintyFillOpacity, other.seriesUncertaintyFillOpacity, t)!,
    );
  }
}

Map<String, double> spacingForDensity(DensityMode mode) {
  switch (mode) {
    case DensityMode.comfortable:
      return {'xs': 4, 'sm': 8, 'md': 16, 'lg': 24, 'xl': 32, '2xl': 48, '3xl': 64};
    case DensityMode.compact:
      return {'xs': 3, 'sm': 6, 'md': 12, 'lg': 18, 'xl': 24, '2xl': 36, '3xl': 48};
    case DensityMode.dense:
      return {'xs': 2, 'sm': 4, 'md': 8, 'lg': 12, 'xl': 16, '2xl': 24, '3xl': 32};
  }
}

ThemeData buildSummaTheme() {
  final tnum = const [FontFeature.tabularFigures()];

  return ThemeData.dark().copyWith(
    scaffoldBackgroundColor: const Color(0xFF0B0D11),
    splashColor: Colors.transparent,
    highlightColor: Colors.transparent,
    textTheme: TextTheme(
      displayLarge: GoogleFonts.bricolageGrotesque(
        fontSize: 64,
        fontWeight: FontWeight.w700,
        height: 1.0,
        letterSpacing: -1.92,
        fontFeatures: tnum,
      ),
      bodyLarge: GoogleFonts.dmSans(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        height: 1.6,
        fontFeatures: tnum,
      ),
      labelSmall: GoogleFonts.jetBrainsMono(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        letterSpacing: 0.6,
        fontFeatures: tnum,
      ),
    ),
    extensions: <ThemeExtension<dynamic>>[
      SummaTheme.dark,
    ],
  );
}

---

## БЛОК 18: Versioning & Change Policy

### Version Format

`v{major}.{minor}` — например `v3.2`.

| Change type | Version bump | Примеры |
|-------------|-------------|---------|
| **Breaking** (удаление/переименование токена, изменение semantic mapping) | Major | Удалить `--data-gov`, переименовать `--accent` → `--brand-primary` |
| **Additive** (новый токен, новый chart type rule, новый компонент) | Minor | Добавить `--data-agriculture`, добавить Treemap rules |
| **Correction** (typo fix, contrast ratio update, value tweak) | Minor | Исправить hex-код, обновить contrast pair |

### Rules

1. **Никогда не удалять токен без deprecation notice в предыдущей версии.** Сначала `/* DEPRECATED v3.2: use --data-xxx instead */`, удаление — в следующем major.
2. **Каждое изменение документируется** в changelog в конце файла с датой и причиной.
3. **Breaking changes требуют grep по codebase** (CSS + Flutter + D3/chart code) и обновления всех consumers в том же PR.
4. **Новые chart type rules** добавляются в Data Viz Canon без breaking change — это additive.
5. **Foundation raw values** (`--raw-*`) могут меняться, но semantic tokens (`--bg-surface`, `--data-gov`) должны сохранять своё назначение.

### Changelog

| Version | Date | Change |
|---------|------|--------|
| v3.0 | 2025-04 | Initial production system. 4-layer tokens, Data Viz Canon, Accessibility, Export rules. |
| v3.1 | 2025-04 | Added: Data Reliability & Uncertainty (Block 10), Chart Behavior Semantics, Layering & Elevation (Block 13), Localization (Block 14), Waterfall & Small Multiples rules, Chart Modes (Editorial/Operational), Export Governance, SR Fallback, content rule #6 and #7. |
| v3.2 | 2025-04 | Added: CSS behavior tokens (series-*, suppressed-pattern-*), concrete suppressed data visual spec (StatCan/CMHC convention), refined spline smoothing rule scope, full Flutter copyWith/lerp with chart behavior tokens, Versioning & Change Policy (Block 18). |

---

Design System v3.2 — Summa Vision. Обновляется при изменении бренда, добавлении платформ, локализации, правилах неопределённости данных и по результатам user testing.
