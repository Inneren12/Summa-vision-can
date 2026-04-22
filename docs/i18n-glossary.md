# Summa Vision — Bilingual Glossary (EN → RU)

## How to read this file

This file is organised into **concept layers**. Each section belongs to exactly one layer:

| Layer | Sections | Used in |
|---|---|---|
| Domain glossary | §1 Product & entity, §2 Editor & design, §3 Data & dataset, §8 Canadian domain | Translation context, LLM prompts |
| UI actions (verbs) | §4 Workflow & action | `messages/en.json` action keys, button labels |
| UI statuses (adjectives/nouns) | §5 Status & state | `messages/en.json` status keys, badge labels |
| Validation messages | §6 Validation & error | `messages/en.json` validation keys |
| Technical keep-EN list | §7 Technical terms | Reference list — do not translate |
| Plural metadata | §9 Plural forms | ARB/ICU plural blocks |

**Rule:** When writing i18n keys, use the layer to determine the appropriate role suffix.
A term in §4 (action layer) should use an action-compatible role suffix such as `.verb` or `.action`
(e.g. `publish.verb`, `draft.action`).
A term in §5 (status layer) should use `.status` (e.g. `published.status`, `draft.status`).
The full key format is always `{term}.{grammatical_role}` — see key naming scheme below.

## Key naming scheme (flat namespace, variant A)

All i18n keys follow this pattern: `{term}.{grammatical_role}`

**Approved roles:**
| Role suffix | Meaning | Example key | Example EN value |
|---|---|---|---|
| `.noun` | Standalone noun (entity name) | `filter.noun` | "Filter" |
| `.verb` | Imperative button label | `filter.verb` | "Filter" |
| `.action` | Verb phrase for workflow action | `draft.action` | "Save as Draft" |
| `.status` | State badge / status label | `draft.status` | "Draft" |
| `.mode` | Mode toggle label | `preview.mode` | "Preview" |
| `.title` | Section/page heading | `preview.title` | "Preview" |
| `.label` | Form field label | `filter.label` | "Filter by" |
| `.placeholder` | Input placeholder | `search.placeholder` | "Search…" |
| `.empty` | Empty state message | `publications.empty` | "No publications yet." |
| `.confirm` | Confirmation dialog body | `delete.confirm` | "Are you sure?" |
| `.nav` (or `nav.*`) | Navigation control label | `nav.back` | "Back" |

**Rule:** A term that appears in multiple grammatical roles MUST have separate keys.
Never share one key between a button label and a status badge.

**Examples of correct multi-role entries:**
- `draft.status` → "Черновик" (badge)
- `draft.action` → "Сохранить как черновик" (button)
- `preview.mode` → "Предпросмотр" (mode toggle)
- `filter.noun` → "Фильтр" (entity)
- `filter.verb` → "Фильтровать" (button)
- `import.noun` → "Импорт" (section heading)
- `import.verb` → "Импортировать" (button)

Status: DRAFT — pending review by founder.

## Section 1 — Product & entity terms

Terms for core platform concepts, user-facing entities, document lifecycle.

| Term (EN) | Canonical RU | Allowed variants | Forbidden variants | Grammar / UI role | Notes |
|---|---|---|---|---|---|
| publication | публикация |  |  | noun | Базовый термин для опубликованного материала. |
| graphic | графика |  |  | noun | Для отдельной визуальной единицы. |
| infographic | инфографика |  |  | noun | Основной тип контента в продукте. |
| dashboard | дашборд |  |  | noun | Устоявшийся термин в русскоязычной аналитике. |
| page | страница |  |  | noun | Страница внутри публикации или проекта. |
| section | раздел |  |  | noun | Логическая часть документа или панели. |
| layout | макет |  |  | noun | Для структуры размещения элементов. |
| document | документ |  |  | noun | Универсальный контейнер контента. |
| template | шаблон |  |  | noun | Предустановленная заготовка. |
| project | проект |  |  | noun | Рабочая сущность верхнего уровня. |
| admin panel | панель администратора | админ-панель (informal only) | *(none)* | noun | Канон: "панель администратора". |
| gallery | галерея |  |  | noun | Экран с карточками материалов. |
| home | Главная |  |  | noun | Key: nav.home — navigation label only, not a general-purpose term. Always rendered Title Case ("Главная") in nav menus by UI convention. Do not use lowercase "главная" as a standalone label in buttons or headings. |
| login | вход |  |  | noun | Существительное для названия экрана/пункта. |
| logout | выход |  |  | noun | Существительное для пункта меню аккаунта. |
| account | аккаунт |  | учетная запись | noun | Более естественно для продукта. |
| subscription | подписка |  |  | noun | Тарифная/биллинг-сущность. |
| pricing | тарифы |  |  | noun | Для страницы с планами и ценами. |

## Section 2 — Editor & design terms

Terms specific to the infographic editor: blocks, layouts, palettes, typography, canvas, inspector.

| Term (EN) | Canonical RU | Allowed variants | Forbidden variants | Grammar / UI role | Notes |
|---|---|---|---|---|---|
| block | блок |  |  | noun | Базовый элемент конструктора. |
| chart | график |  |  | noun | Для chart как визуализации данных. |
| table | таблица |  |  | noun | Табличный блок. |
| text block | текстовый блок |  |  | noun | Специализированный тип блока. |
| headline | заголовок |  |  | noun | Крупный заголовок секции/карточки. |
| subtitle | подзаголовок |  |  | noun | Вторичный заголовок. |
| KPI | KPI |  |  | noun | Оставлять как KPI. |
| bar chart | столбчатая диаграмма |  |  | noun | Стандартный термин в BI/аналитике. |
| line chart | линейный график |  |  | noun | Стандартный термин. |
| comparison | сравнение |  |  | noun | Режим или блок сравнения. |
| palette | палитра |  |  | noun | Цветовая палитра. |
| theme | тема |  |  | noun | Тема оформления. |
| colour | цвет |  |  | noun | Каноническая локализация UI-атрибута. |
| typography | типографика |  |  | noun | Раздел настроек текста. |
| font | шрифт |  |  | noun | Семейство/гарнитура шрифта. |
| canvas | холст |  |  | noun | Рабочая область редактора. |
| inspector | инспектор |  |  | noun | Правая панель свойств, устоявшийся термин. |
| sidebar | боковая панель |  |  | noun | Левая/правая навигационная панель. |
| toolbar | панель инструментов |  |  | noun | Верхняя или плавающая панель действий. |
| preview | предпросмотр |  |  | noun | Режим просмотра перед публикацией. |
| zoom | масштаб |  |  | noun | Параметр масштаба. |
| grid | сетка |  |  | noun | Сетка выравнивания. |
| snap | привязка |  |  | noun | Привязка к сетке/направляющим. |
| safe zone | безопасная зона |  |  | noun | Область без риска обрезки контента. |
| margins | поля |  |  | noun | Внешние отступы контейнера. |
| padding | внутренний отступ |  |  | noun | Внутренние отступы; в UI можно сокращать до "отступ". |
| background | фон |  |  | noun | Фоновый слой/цвет. |
| foreground | передний план |  |  | noun | Элементы поверх фона. |
| layer | слой |  |  | noun | Слой в композиции. |
| delta badge | маркер изменения | бейдж дельты (internal slang only) |  | noun |  |
| eyebrow tag | надзаголовок |  |  | noun | Короткая метка над основным заголовком. |
| source footer | подпись источника | подвал источника (informal) |  | noun |  |
| brand stamp | фирменная метка |  |  | noun | Небольшой брендовый маркер; не "штамп" во избежание канцелярского оттенка. |
| hero stat | ключевой показатель | главный показатель |  | noun | Крупное центральное значение в hero-блоке. |
| data binding | привязка данных |  |  | noun | Связь поля данных с элементом интерфейса. |

## Section 3 — Data & dataset terms

Terms for StatCan/CMHC datasets, cubes, data binding, data fields, publication metadata.

| Term (EN) | Canonical RU | Allowed variants | Forbidden variants | Grammar / UI role | Notes |
|---|---|---|---|---|---|
| dataset | набор данных |  |  | noun | Канонический термин в data-продуктах. |
| cube | куб |  |  | noun | Термин для многомерного статистического куба. |
| data series | ряд данных |  |  | noun | Временной или категориальный ряд. |
| data point | точка данных |  |  | noun | Отдельное наблюдение на графике/в наборе. |
| data field | поле данных |  |  | noun | Отличать от form field. |
| value | значение |  |  | noun | Числовое или текстовое значение поля. |
| label | метка |  |  | noun | Подпись серии/категории. |
| unit | единица измерения |  |  | noun | Например: %, CAD, индекс. |
| dimension | измерение |  |  | noun | Измерение в OLAP/кубе. |
| frequency | частота |  |  | noun | Частота наблюдений: monthly, quarterly и т.д. |
| time period | период |  |  | noun | Отрезок времени наблюдения. |
| observation | наблюдение |  |  | noun | Единичная статистическая запись. |
| indicator | индикатор |  |  | noun | Макроэкономический индикатор. |
| metric | метрика |  |  | noun | Внутренняя или аналитическая метрика. |
| data source | источник данных |  |  | noun | Источник: StatCan, CMHC и др. |
| cube catalog | каталог кубов |  |  | noun | Список доступных статистических кубов. |
| StatCan cube | куб StatCan |  |  | noun | Название источника не переводится. |
| data sync | синхронизация данных |  |  | noun | Процесс синхронизации с источником. |
| data refresh | обновление данных |  |  | noun | Перезагрузка данных из источника. |
| ETL | ETL |  |  | noun | Оставлять как ETL. |
| import | импорт |  |  | noun | Существительное для операции/раздела. |
| bind field | привязать поле |  |  | verb | Кнопка/действие в редакторе. |
| unbind | отвязать |  |  | verb | Разорвать связь поля с элементом. |
| filter | фильтр |  |  | noun | Существительное для сущности фильтра. |
| aggregation | агрегация |  |  | noun | Суммирование/группировка данных. |
| record | запись |  |  | noun | Key: record.noun |
| row | строка |  |  | noun | Key: row.noun |
| column | столбец |  |  | noun | Key: column.noun |

## Section 4 — Workflow & action terms

Verbs users invoke: publish, draft, save, export, validate, review, etc.

| Term (EN) | Canonical RU | Allowed variants | Forbidden variants | Grammar / UI role | Notes |
|---|---|---|---|---|---|
| Save | Сохранить |  |  | verb | Кнопка действия. |
| Publish | Опубликовать |  |  | verb | Кнопка публикации. |
| Unpublish | Снять с публикации |  | Депаблишить, Снять публикацию | verb |  |
| Draft | Сохранить как черновик |  |  | verb | Key: draft.action — button only. |
| Submit | Отправить |  |  | verb | Отправить на проверку/согласование. |
| Review (action) | Проверить | *(none)* | Рецензировать (too formal for UI) | verb | Key: review.verb — imperative button label |
| In review (status) | На проверке | На проверку (transition label) | *(none)* | noun/status | Key: review.status — workflow step badge |
| Approve | Одобрить |  |  | verb | Подтвердить публикацию/изменение. |
| Reject | Отклонить |  |  | verb | Отклонить запрос/изменение. |
| Delete | Удалить |  |  | verb | Удаление сущности окончательно. |
| Remove | Убрать |  |  | verb | Мягкое удаление из текущего контекста. |
| Archive | Архивировать |  |  | verb | Перевести в архив. |
| Duplicate | Дублировать |  |  | verb | Создать копию рядом. |
| Copy | Копировать |  |  | verb | Буфер обмена. |
| Cut | Вырезать |  |  | verb | Буфер обмена. |
| Paste | Вставить |  |  | verb | Буфер обмена. |
| Undo | Отменить |  |  | verb | Отменить последнее действие. |
| Redo | Повторить |  |  | verb | Вернуть отмененное действие. |
| Edit | Редактировать |  |  | verb | Перейти к правке. |
| Add | Добавить |  |  | verb | Добавить сущность/элемент. |
| Create | Создать |  |  | verb | Создание новой сущности. |
| Update | Обновить |  |  | verb | Обновить существующую сущность/данные. |
| Upload | Загрузить |  |  | verb | Загрузить файл в систему. |
| Download | Скачать |  |  | verb | Скачать файл из системы. |
| Export | Экспортировать |  |  | verb | Key: export.verb — action button. |
| Import | Импортировать |  |  | verb | Key: import.verb — action button. |
| Preview | Предпросмотр | *(none)* | *(none)* | noun/mode | Key: preview.mode — mode toggle label, NOT a verb. Button label is the noun form. |
| Render | Рендерить | Визуализировать (if public-facing context required) | *(none)* | verb | Key: render.verb — EDITOR/INTERNAL ONLY. Do not use in public-facing UI or operator onboarding copy. If a user-friendly label is needed, use "Визуализировать" from allowed variants. |
| Sync | Синхронизировать |  |  | verb | Запустить синхронизацию. |
| Refresh | Обновить |  |  | verb | Обновить экран/данные. |
| Cancel | Отменить |  |  | verb | Отмена действия/диалога. |
| Close | Закрыть |  |  | verb | Закрыть окно/панель. |
| Open | Открыть |  |  | verb | Открыть файл/экран. |
| Back | Назад | *(none)* | *(none)* | nav | Key: nav.back — navigation control label, not a grammatical verb. Used in back-buttons and breadcrumb navigation. |
| Next | Далее | *(none)* | *(none)* | nav | Key: nav.next — navigation control label, not a grammatical verb. Used in wizard/step navigation. |
| Apply | Применить |  |  | verb | Применить настройки/фильтр. |
| Reset | Сбросить |  |  | verb | Сбросить значения к исходным. |
| Search | Найти | *(none)* | *(none)* | verb | Key: search.verb — search button label (imperative). |
| Search (noun) | Поиск | *(none)* | *(none)* | noun | Key: search.noun — search section heading or field label. |
| Search placeholder | Поиск… | Найти… | *(none)* | noun | Key: search.placeholder — input placeholder text. Use ellipsis (…), not three dots (...). |
| Filter | Фильтровать |  |  | verb | Key: filter.verb — action button. |
| Sort | Сортировать |  |  | verb | Действие сортировки. |
| Try again | Повторить |  |  | verb | Повторить неуспешную операцию. |
| Continue | Продолжить |  |  | verb | Продолжить сценарий. |
| Confirm | Подтвердить |  |  | verb | Подтвердить выбор/операцию. |

## Section 4b — Generic UI nouns

Count-based nouns used across UI layers that do not belong to a specific domain section.
These are referenced by the plural table in Section 9.

| Term (EN) | Canonical RU | Allowed variants | Forbidden variants | Grammar / UI role | Notes |
|---|---|---|---|---|---|
| result | результат | *(none)* | *(none)* | noun | Key: result.noun |
| item | элемент | *(none)* | *(none)* | noun | Key: item.noun — generic list element |
| change | изменение | *(none)* | *(none)* | noun | Key: change.noun |
| issue | проблема | *(none)* | *(none)* | noun | Key: issue.noun — validation/QA context |
| thread | ветка | *(none)* | тред (loanword, grammatically unstable) | noun | Key: thread.noun — used for comment threads in review/discussion contexts. Plural: ветка / ветки / веток. |
| day | день | *(none)* | *(none)* | noun | Key: time.day — used in duration/date labels |
| week | неделя | *(none)* | *(none)* | noun | Key: time.week |
| month | месяц | *(none)* | *(none)* | noun | Key: time.month |
| year | год | *(none)* | *(none)* | noun | Key: time.year |
| hour | час | *(none)* | *(none)* | noun | Key: time.hour |
| minute | минута | *(none)* | *(none)* | noun | Key: time.minute |
| second | секунда | *(none)* | *(none)* | noun | Key: time.second |

## Section 5 — Status & state terms

Adjectives/nouns for state display: Published, Draft, Saving, Error, etc.

| Term (EN) | Canonical RU | Allowed variants | Forbidden variants | Grammar / UI role | Notes |
|---|---|---|---|---|---|
| Draft | Черновик |  |  | noun | Key: draft.status — badge only. |
| Published | Опубликовано | *(none)* | *(none)* | adjective | Key: published.status — short predicative form (краткое причастие). Gender-neutral in badge context. Agrees with publication (ср.р.) by convention; do not inflect for other genders in UI. |
| Saving | Сохранение... |  |  | noun | Процесс в реальном времени. |
| Saved | Сохранено |  |  | adjective | Успешное сохранение завершено. |
| Unsaved | Не сохранено |  |  | adjective | Есть несохраненные изменения. |
| Loading | Загрузка... |  |  | noun | Процесс загрузки. |
| Loaded | Загружено |  |  | adjective | Данные/ресурс загружены. |
| Processing | Обработка... |  |  | noun | Фоновая обработка. |
| Error | Ошибка |  |  | noun | Ошибочное состояние. |
| Warning | Предупреждение |  |  | noun | Неблокирующая проблема. |
| Success | Выполнено | Успешно (toast/result adverb only) | Готово (use completed.status instead) | adjective | Key: success.status — use for operation-result badges. For toast messages use adverb form "Успешно" as allowed variant. Do NOT use as generic universal status — prefer specific states (published.status, saved.status, completed.status). FUTURE: avoid new usages of success.status; this key is a transitional placeholder and may be deprecated post-launch. |
| Pending | В ожидании |  |  | adjective | Ожидание обработки/решения. |
| Completed | Завершено |  |  | adjective | Процесс завершен полностью. |
| Failed | Не удалось | Не выполнено (process context) | Ошибка (use `error` key instead) | adjective | Операция завершилась неуспешно. |
| Active | Активен |  |  | adjective | Для объекта мужского рода; в UI может согласовываться по роду. |
| Inactive | Неактивен |  |  | adjective | Парный статус к "Активен". |
| Enabled | Включено |  |  | adjective | Функция включена. |
| Disabled | Отключено |  |  | adjective | Функция отключена. |
| Online | В сети |  |  | adjective | Сетевой статус. |
| Offline | Не в сети |  |  | adjective | Нет подключения к сети/сервису. |
| Connected | Подключено |  |  | adjective | Verify context: network state vs. data binding. |
| Disconnected | Отключено | Соединение разорвано (verbose) |  | adjective |  |
| Required | Обязательно |  |  | adjective | Обязательное поле/параметр. |
| Optional | Необязательно |  |  | adjective | Необязательное поле/параметр. |

## Section 6 — Validation & error terms

Validation messages, error types.

| Term (EN) | Canonical RU | Allowed variants | Forbidden variants | Grammar / UI role | Notes |
|---|---|---|---|---|---|
| Required field | Обязательное поле |  |  | phrase | Текст валидации формы. |
| Invalid format | Неверный формат |  |  | phrase | Ошибка структуры ввода. |
| Out of range | Вне диапазона |  |  | phrase | Значение не входит в допустимые границы. |
| Contrast too low | Недостаточный контраст |  |  | phrase | Сообщение accessibility-проверки. |
| WCAG AA | WCAG AA |  |  | noun | Стандарт оставлять без перевода. |
| accessibility | доступность |  |  | noun | Доступность интерфейса для всех пользователей. |
| validation | валидация |  |  | noun | Процесс проверки корректности. |
| warning | предупреждение |  |  | noun | Неблокирующая диагностическая запись. |
| error | ошибка |  |  | noun | Блокирующая или критическая проблема. |
| critical | критический |  |  | adjective | Уровень серьезности ошибки. |
| missing data | отсутствуют данные |  |  | phrase | Нет данных для построения/расчета. |
| stale data | устаревшие данные |  |  | phrase | Данные не обновлялись дольше порога. |
| rate limit exceeded | превышен лимит запросов |  |  | phrase | Частая API-ошибка; использовать именно "лимит запросов". |
| verification failed | проверка не пройдена |  |  | phrase | Ошибка проверки токена/условий. |
| session expired | сессия истекла |  |  | phrase | Нужен повторный вход. |
| unauthorized | не авторизован |  |  | phrase | Нет действительной авторизации. |
| forbidden | доступ запрещен |  |  | phrase | Авторизация есть, но прав недостаточно. |
| not found | не найдено |  |  | phrase | Ресурс отсутствует. |

## Section 7 — Technical terms (kept in English)

Anglicisms and technical terms that stay English in Russian UI.

| Term (EN) | Notes |
|---|---|
| API | Стандартный технический термин, не переводится. |
| SDK | Стандартный технический термин, не переводится. |
| URL | Стандартный технический термин, не переводится. |
| HTTPS | Протокол, не переводится. |
| SSL | Протокол/сертификаты, не переводится. |
| CDN | Инфраструктурный термин, не переводится. |
| JSON | Формат данных, не переводится. |
| CSV | Формат данных, не переводится. |
| SVG | Формат графики, не переводится. |
| PNG | Формат изображения, не переводится. |
| JPG | Формат изображения, не переводится. |
| PDF | Формат документа, не переводится. |
| DOM | Термин фронтенд-разработки, не переводится. |
| UI | Термин продуктового дизайна, не переводится. |
| UX | Термин продуктового дизайна, не переводится. |
| SaaS | Модель продукта, не переводится. |
| B2B | Сегмент, не переводится. |
| B2C | Сегмент, не переводится. |
| CEO | Роль, в UI оставлять аббревиатуру. |
| CTO | Роль, в UI оставлять аббревиатуру. |
| CFO | Роль, в UI оставлять аббревиатуру. |
| MVP | Продуктовый термин, не переводится. |
| SEO | Маркетинговый термин, не переводится. |
| QA | Термин процесса разработки, не переводится. |
| CI | DevOps-термин, не переводится. |
| CD | DevOps-термин, не переводится. |
| StatCan | Бренд источника данных, не переводится. |
| CMHC | Аббревиатура организации, не переводится. |
| WCAG | Стандарт доступности, не переводится. |
| Cloudflare | Название сервиса, не переводится. |
| Turnstile | Название продукта Cloudflare, не переводится. |
| OAuth | Протокол авторизации, не переводится. |
| JWT | Формат токена, не переводится. |

## Section 8 — Canadian domain terms

StatCan / CMHC / Canadian real estate specific terminology.

| Term (EN) | Canonical RU | Allowed variants | Forbidden variants | Grammar / UI role | Notes |
|---|---|---|---|---|---|
| Statistics Canada | Статистическое управление Канады |  |  | noun | Официальное русское описание организации. |
| Statistique Canada | Статистическое управление Канады |  |  | noun | Франкоязычное официальное имя, в RU можно унифицировать перевод. |
| StatCan | StatCan |  |  | noun | Бренд сохраняется на английском. |
| Canada Mortgage and Housing Corporation | Канадская ипотечная и жилищная корпорация |  |  | noun | Устоявшийся перевод названия CMHC. |
| CMHC | CMHC |  |  | noun | Аббревиатуру не переводить. |
| housing starts | начатое строительство жилья |  |  | noun | Канонический термин статистики строительства. |
| housing completions | завершенное строительство жилья |  |  | noun | Парный показатель к housing starts. |
| housing under construction | жилье в стадии строительства |  |  | noun | Текущее незавершенное строительство. |
| dwelling unit | жилое помещение |  |  | noun | Универсальный нормативный термин. |
| CMA (Census Metropolitan Area) | CMA (переписная агломерация) |  |  | noun | Сокращение CMA сохраняется, расшифровка дана в скобках. |
| province | провинция |  |  | noun | Административная единица Канады. |
| territory | территория |  |  | noun | Для Yukon, Nunavut, Northwest Territories. |
| First Nations | Первые нации |  |  | noun | Принятая форма для Indigenous peoples в канадском контексте. |
| Quebec | Квебек |  |  | noun | Фиксированная форма по требованию. |
| Ontario | Онтарио |  |  | noun | Фиксированная форма по требованию. |
| Vancouver | Ванкувер |  |  | noun | Топоним. |
| Toronto | Торонто |  |  | noun | Топоним. |
| Calgary | Калгари |  |  | noun | Топоним. |
| Ottawa | Оттава |  |  | noun | Топоним. |
| Montreal | Монреаль |  |  | noun | Фиксированная форма по требованию. |
| benchmark price | эталонная цена |  |  | noun | Стандартный перевод термина рынка жилья. |
| MLS HPI | индекс цен на жилье MLS |  |  | noun | HPI передается как "индекс цен на жилье". |
| fixed mortgage | ипотека с фиксированной ставкой |  |  | noun | Финансовый термин. |
| variable mortgage | ипотека с плавающей ставкой |  |  | noun | Финансовый термин. |
| METR (Marginal Effective Tax Rate) | METR (предельная эффективная налоговая ставка) |  |  | noun | Сокращение сохраняется, расшифровка переводится. |
| principal residence | основное место проживания |  |  | noun | Налогово-правовой термин для primary home. |

## Section 9 — Plural forms reminder

Russian has 3 plural forms. For count-based strings, these forms are needed:
- 1, 21, 31, 41... → "one" (именительный падеж, единственное число)
- 2-4, 22-24... → "few" (родительный падеж, единственное число)
- 0, 5-20, 25-30... → "many" (родительный падеж, множественное число)

Example: "page" → 1 страница / 2 страницы / 5 страниц.

List all count-based nouns from previous sections with their three forms:

| Noun | Source section | one (1) | few (2-4) | many (5+) |
|---|---|---|---|---|
| page | §1 | страница | страницы | страниц |
| block | §2 | блок | блока | блоков |
| section | §1 | раздел | раздела | разделов |
| publication | §1 | публикация | публикации | публикаций |
| chart | §2 | график | графика | графиков |
| cube | §3 | куб | куба | кубов |
| dataset | §3 | набор данных | набора данных | наборов данных |
| observation | §3 | наблюдение | наблюдения | наблюдений |
| record | §3 | запись | записи | записей |
| row | §3 | строка | строки | строк |
| column | §3 | столбец | столбца | столбцов |
| error | §6 | ошибка | ошибки | ошибок |
| warning | §6 | предупреждение | предупреждения | предупреждений |
| day | §4b | день | дня | дней |
| week | §4b | неделя | недели | недель |
| month | §4b | месяц | месяца | месяцев |
| year | §4b | год | года | лет |
| hour | §4b | час | часа | часов |
| minute | §4b | минута | минуты | минут |
| second | §4b | секунда | секунды | секунд |
| change | §4b | изменение | изменения | изменений |
| issue | §4b | проблема | проблемы | проблем |
| thread | §4b | ветка | ветки | веток |
| item | §4b | элемент | элемента | элементов |
| result | §4b | результат | результата | результатов |
